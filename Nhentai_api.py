import requests
import os
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

RESPONSE_OK = 200
RESPONSE_BUSY = 503


class ApiConfig:
    verify_ssl = True
    retry_wait_time = 0.5


class Book:
    book_info: dict

    # Initialize a book given a book id or book info json
    def __init__(self, book_id, book_info=None):
        if book_info is None:
            self.book_id = book_id
            self.book_info = self.get_book_info()
        else:
            self.book_id = book_info["id"]
            self.book_info = book_info
        self.bad = False

        # If we failed for some reason, set the bad flag to True, signalling that this book can not be downloaded
        if self.book_info == "":
            self.bad = True
            return

        # The media id is used to get the pages from a book.
        # Example https://i.nhentai.net/galleries/770497/8.jpg
        # Where 770497 is the media id and 8 is the page number
        self.media_id = self.book_info["media_id"]
        self.page_count = self.book_info["num_pages"]
        self.name = self.book_info["title"]["english"]


    # Get some info about the book via an api call about the book, which will grant info such as media id and page count
    # Example: https://nhentai.net/api/gallery/233960
    def get_book_info(self):
        while True:
            url = "https://nhentai.net/api/gallery/" + str(self.book_id)
            resp = requests.get(url=url, verify=ApiConfig.verify_ssl)

            # The response will be the html of the response page
            # If we are good to go, return the json
            if resp.status_code == RESPONSE_OK:
                data = resp.json()
                return data
            # If the server is busy, try again
            elif resp.status_code == RESPONSE_BUSY:
                continue
            # If there is another error which we do not know how to handle, signal an error by returning ""
            # We also print the error to give the developer a heads up
            else:
                print("a man has fallen into the lego river because of " + str(resp.status_code))
                return ""


    def get_image_type(self, page):
        if page == 0:
            image_type = self.book_info["images"]["thumbnail"]["t"]
        else:
            image_type = self.book_info["images"]["pages"][page - 1]["t"]

        if image_type == "j":
            return "jpg"
        elif image_type == "p":
            return "png"
        else:
            print(f"Unknown image type \"f{image_type}\" on page {page}")
            return "jpg"


    def get_image_link(self, page):
        if page == 0:
            return f"https://t.nhentai.net/galleries/{self.media_id}/cover.{self.get_image_type(0)}"
        else:
            return f"https://i.nhentai.net/galleries/{self.media_id}/{page}.{self.get_image_type(page)}"


    def get_cover(self):
        response = requests.get(self.get_image_link(0), verify=ApiConfig.verify_ssl)
        file = BytesIO(response.content)
        file.name = "cover.jpg"
        return file


    @staticmethod
    def save_image_full(media_id, path, page, image_type):
        try:
            # If the image already exists, pass
            if os.path.isfile(path):
                return

            url = f"https://{'t' if page == 0 else 'i'}.nhentai.net/galleries/{media_id}/{'cover' if page == 0 else page}.{image_type}"
            # Example url: https://i.nhentai.net/galleries/770497/8.jpg
            # Download the image
            response = requests.get(url, verify=ApiConfig.verify_ssl)

            # If we get a 503, wait and try again
            retry_time = ApiConfig.retry_wait_time
            while True:
                if response.status_code == RESPONSE_BUSY:
                    time.sleep(retry_time)
                    response = requests.get(url, verify=ApiConfig.verify_ssl)
                    retry_time *= 1.5
                else:
                    break

            if response.status_code != RESPONSE_OK:
                print(f"Error downloading {url}\nError code: {response.status_code}\nMedia id: {media_id}\nImage type: {image_type}")
                return

            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            with open(path, 'wb') as file:
                file.write(response.content)

        except Exception as e:
            print(e)


    def save_image(self, path, page):
        save_image(self.media_id, path, page, self.get_image_link(page))


    def save_all_images(self, path):
        if self.bad:
            return

        name = self.name
        black_list = ["/","\\",":","*","?","\"","<",">","|"]
        for letter in black_list:
            path = path.replace(letter, "")
            name = name.replace(letter, "")
            
        # Multithread the book downloading
        image_downloader = ThreadPoolExecutor(self.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(self.page_count + 1):
            image_downloader.submit(Book.save_image_full, self.media_id, f"{path}/{name}/{'cover' if page == 0 else page}.{self.get_image_type(page)}", page, self.get_image_type(page))

        image_downloader.shutdown()


class Search:
    # Initialize information about a certain query and all the books in that page
    def __init__(self, query, page=1, popular=False):
        self.query = query
        self.popular = popular
        self.page = page
        self.search_info = self.get_search_info()
        self.result = self.search_info["result"]
        self.page_amount = self.search_info["num_pages"]
        self.books_per_page = self.search_info["per_page"]
        self.books = []

        # max(1, len(self.result)) is to make sure that the amount of workers is > 0, otherwise we get an error
        executor = ThreadPoolExecutor(max(1, len(self.result)))
        # Fill our book list with empty entries, as we will initialize it concurrently
        self.books = [None] * len(self.result)

        # Initialize books concurrently, as making all api requests asking about books with a single thread is slow
        for i, book in enumerate(self.result):
            executor.submit(Search.create_book, self.search_info["result"][i], self.books, i)

        # Wait for all books to be initialized properly. Could be optimized by proceeding with the ones that are done?
        executor.shutdown()


    # Make a query to nhentai about a certain search query and other parameters
    # Example url: https://nhentai.net/api/galleries/search?query=females%20only&page=2&sort=popular
    def get_search_info(self):
        sort = "popular" if self.popular else ""
        url = f"https://nhentai.net/api/galleries/search?query={self.query}&page={self.page}&sort={sort}"

        resp = requests.get(url=url, verify=ApiConfig.verify_ssl)
        data = resp.json()
        return data


    def go_to_page(self, page):
        self.__init__(self.query, page, self.popular)


    # Method for creating a book (used in multithreading)
    @staticmethod
    def create_book(book_info, book_list, i):
        book_list[i] = Book(-1, book_info=book_info)


    @staticmethod
    def save_book(book, directory):
        # Multithread the book downloading
        image_downloader = ThreadPoolExecutor(book.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(book.page_count + 1):
            image_downloader.submit(Book.save_image_full, book.media_id, f"{directory}/{page}.{book.get_image_type(page)}", page, book.get_image_type(page))

        image_downloader.shutdown()


    def download_books(self, directory):
        executor = ThreadPoolExecutor(len(self.books))
        for i, book in enumerate(self.books):
            # Do not save bad books
            if book.bad:
                continue

            # Remove illegal characters illegal for files/ folder in windows
            name = book.name
            black_list = ["/","\\",":","*","?","\"","<",">","|"]
            for letter in black_list:
                name = name.replace(letter, "")
            file_path = f"{directory}/{name}"

            # Create a folder for the book if it does not exist
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            # Start downloading the book concurrently
            executor.submit(Search.save_book, book, file_path)

        # Wait for all downloads to finish
        executor.shutdown()
