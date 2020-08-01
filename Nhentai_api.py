import requests
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

RESPONSE_OK = 200
RESPONSE_BUSY = 503

class ApiConfig:
    verify_ssl = True

class Book:
    # Get some info about the book via an api call about the book, which will grant info such as media id and page count
    # Example: https://nhentai.net/api/gallery/233960
    def GetBookInfo(self):

        while True:
            url = "https://nhentai.net/api/gallery/" + str(self.book_id)
            resp = requests.get(url=url, verify=ApiConfig.verify_ssl, headers = {'User-agent': 'Nhentai-api'})

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
    def __init__(self, bookId):
        self.book_id = bookId
        self.book_info = self.GetBookInfo()
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

    def GetCover(self):
        url = f"https://t.nhentai.net/galleries/{self.media_id}/cover.jpg"
        response = requests.get(url, verify=ApiConfig.verify_ssl)
        file = BytesIO(response.content)
        file.name = "cover.jpg"
        return file

    def SaveImage(self, path, page, imageType):
        # If the image already exists, pass
        if os.path.isfile(path):
            return

        url = "https://i.nhentai.net/galleries/" + str(self.media_id) + "/" + str(page) + imageType
        # Example url: https://i.nhentai.net/galleries/770497/8.jpg
        # Download the image
        response = requests.get(url, verify=ApiConfig.verify_ssl)
        if response.status_code != RESPONSE_OK:
            print("Error downloading " + url)
            print("Error code: " + str(response.status_code))
            print("Book id: " + str(self.book_id))
            print("Image type: " + self.book_info["images"]["pages"][page - 1]["t"])

        with open(path, 'wb') as file:
            file.write(response.content)

    def get_image_link(self, page):
        if page == 0:
            return f"https://t.nhentai.net/galleries/{self.media_id}/cover.jpg"
        else:
            image_type = self.book_info["images"]["pages"][page - 1]["t"]
            image_type = "jpg" if image_type == "j" else "png"
            return f"https://i.nhentai.net/galleries/{self.media_id}/{page}.{image_type}"

    # A method for calling saveImage, has to be this way as python cannot pickle class members
    # Here Book is also a function, which when called downloads a book of the provided id
    def __call__(self, dir, page):
        # Get the image type of the current page in the book
        # We index with page - 1 because arrays start at 0 and nhentai books do not
        type = self.book_info["images"]["pages"][page - 1]["t"]
        type = ".jpg" if type == "j" else ".png"

        # Save the image
        self.SaveImage(dir + type, page, type)

    def SaveAllImages(self, path):
        if self.bad:
            return
        # Multithread the book downloading
        imageDownloader = ThreadPoolExecutor(self.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(self.page_count):
            imageDownloader.submit(self, path + "/" + str(page + 1), page + 1)

        imageDownloader.shutdown()

# Method to create a book. Must be outside a class to avoid python's multithreading headaches


class Search:
    # Initialize information about a certain query and all the books in that page
    def __init__(self, query, page=1, popular=False):
        self.query = query
        self.popular = popular
        self.page = page
        self.searchInfo = self.get_search_info()
        self.result = self.searchInfo["result"]
        self.books = []

        executor = ThreadPoolExecutor(len(self.result))
        # Fill our book list with empty entries, as we will initialize it concurrently
        self.books = [None] * len(self.result)

        # Initialize books concurrently, as making all api requests asking about books with a single thread is slow
        for i, book in enumerate(self.result):
            executor.submit(Search.create_book, book["id"], self.books, i)

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

    # Method for creating a book (used in multithreading)
    @staticmethod
    def create_book(book_id, book_list, i):
        book_list[i] = Book(book_id)


    @staticmethod
    def save_book(book, directory):
        # Multithread the book downloading
        image_downloader = ThreadPoolExecutor(book.page_count)

        # The method we call is __call__ of book, which is a wrapper for calling SaveImage
        for page in range(book.page_count):
            image_downloader.submit(book, f"{directory}/{page + 1}", page + 1)

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
