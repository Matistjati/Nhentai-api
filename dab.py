from nhentai_api import *

id = 123946
book = Book(id)

# Create a directory with the same name as the book title
book_dir = book.name
if not os.path.exists(book_dir):
	os.makedirs(book_dir)

# Save all the pages of the book
book.save_all_images(book_dir)
