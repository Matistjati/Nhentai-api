import requests
import urllib
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

RESPONSE_OK = 200
RESPONSE_BUSY = 503

class Page:
    def __init__(self, image, page_number, downloaded, bad):
        self.image = image
        self.page_number = page_number
        self.downloaded = downloaded
        self.bad = bad

    @staticmethod
    def concurrent_init(self, image, page_number, downloaded, bad):
        self.image = image
        self.page_number = page_number
        self.downloaded = downloaded
        self.bad = bad

class Book:
    # Get some info about the book via an api call about the book, which will grant info such as media id and page count
    # Example: https://nhentai.net/api/gallery/233960
    def get_book_info(self):

        while True:
            url = "https://nhentai.net/api/gallery/" + str(self.book_id)
            resp = requests.get(url=url)

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


    # Initialize a book given a book id
    def __init__(self, book_id):
        self.book_id = book_id
        self.book_info = self.get_book_info()
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
        self.images = {}


    def get_cover(self):
        url = f"https://t.nhentai.net/galleries/{self.media_id}/cover.jpg"
        response = requests.get(url)
        file = BytesIO(response.content)
        file.name = "cover.jpg"
        return file


    def get_page(self, page):
        type = self.book_info["images"]["pages"][page - 1]["t"]
        type = "jpg" if type == "j" else "png"
        url = f"https://i.nhentai.net/galleries/{self.media_id}/{page}.{type}"
        print(url)
        response = requests.get(url)
        file = BytesIO(response.content)
        file.name = f"{page}.{type}"
        return file


    def save_image(self, path, page, image_type):
        # If the image already exists, pass
        if os.path.isfile(path):
            return

        url = "https://i.nhentai.net/galleries/" + str(self.media_id) + "/" + str(page) + image_type
        # Example url: https://i.nhentai.net/galleries/770497/8.jpg
        # Download the image
        response = requests.get(url)
        if response.status_code != RESPONSE_OK:
            print("Error downloading " + url)
            print("Error code: " + str(response.status_code))
            print("Book id: " + str(self.book_id))
            print("Image type: " + self.book_info["images"]["pages"][page - 1]["t"])

        with open(path, 'wb') as file:
            file.write(response.content)


    # A method for calling saveImage, has to be this way as python cannot pickle class members
    # Here Book is also a function, which when called downloads a book of the provided id
    def __call__(self, dir, page):
        # Get the image type of the current page in the book
        # We index with page - 1 because arrays start at 0 and nhentai books do not
        type = self.book_info["images"]["pages"][page - 1]["t"]
        type = ".jpg" if type == "j" else ".png"

        # Save the image
        self.SaveImage(dir + type, page, type)


    def save_all_images(self, path):
        if self.bad:
            return
        # Multithread the book downloading
        image_downloader = ThreadPoolExecutor(self.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(self.page_count):
            image_downloader.submit(self, path + "/" + str(page + 1), page + 1)

            image_downloader.shutdown()


    @staticmethod
    def cache_image(self, page):
        image = Book.GetPage(self, page.page_number)
        downloaded = False
        bad = True
        if image.getbuffer().nbytes > 0:
            bad = False
            downloaded = True
        Page.concurrent_init(page, image, page.page_number, downloaded, bad)


    def cache_images(self, center, amount_left, amount_right):
        for i in range(center - amount_left, center + amount_right + 1):
            if i < 0:
                i = self.page_count + i + 1

            if i in self.images and self.images[i].downloaded == True:
                continue
            self.images[i] = Page(BytesIO(), i, False, False)

        executor = ThreadPoolExecutor(len(range(center - amount_left, center + amount_right + 1)))

        for i in range(center - amount_left, center + amount_right + 1):
            if i in self.images and self.images[i].downloaded == True:
                continue
            if i < 0:
                i = self.page_count + i + 1

            executor.submit(Book.CacheImage(self, self.images[i]))

        executor.shutdown()


    def get_image_link(self, page):
        if page == 0:
            return f"https://t.nhentai.net/galleries/{self.media_id}/cover.jpg"

        type = self.book_info["images"]["pages"][page - 1]["t"]
        type = "jpg" if type == "j" else "png"
        url = f"https://i.nhentai.net/galleries/{self.media_id}/{page}.{type}"
        return url


class Search:
    # Make a query to nhentai about a certain search query and other parameters
    # Example url: https://nhentai.net/api/galleries/search?query=females%20only&page=2&sort=popular
    def get_search_info(self):
        sort = "popular" if self.popular else ""
        url = "http://nhentai.net/api/galleries/search?query=" + self.query + "&page=" + str(self.page) + "&sort=" + sort

        resp = requests.get(url=url)
        data = resp.json()
        return data


    @staticmethod
    def create_book(self, id, i):
        self.books[i] = Book(id)


    # Initialize information about a certain query and all the books in that page
    def __init__(self, query, page, popular=False):
        self.query = query
        self.popular = popular
        self.page = page
        self.searchInfo = self.GetSearchInfo()
        self.result = self.searchInfo["result"]
        self.books = []

        executor = ThreadPoolExecutor(len(self.result))
        # Fill our book list with empty entries, as we will initialize it concurrently
        self.books = [None] * len(self.result)

        # Initialize books concurrently, as making all api requests asking about books with a single thread is slow
        for i, book in enumerate(self.result):
            executor.submit(create_book, self, book["id"], i)

        # Wait for all books to be initialized properly. Could be optimized by proceeding with the ones that are done?
        executor.shutdown()


    @staticmethod
    def save_book(book, dir):
        # Multithread the book downloading
        image_downloader = ThreadPoolExecutor(book.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(book.page_count):
            image_downloader.submit(book, dir + "/" + str(page + 1), page + 1)

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
            for character in black_list:
                name = name.replace(character, "")
            dir = directory + name

            # Create a folder for the book if it does not exist
            if not os.path.exists(dir):
                os.makedirs(dir)

            # Start downloading the book concurrently
            executor.submit(Search.save_book, book, dir)

        # Wait for all downloads to finish
        executor.shutdown()
