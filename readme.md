# Nhentai api

Yet another object-oriented nhentai api. Will multithread when downloading multiple things, such as entire books

## Example usage

```
from Nhentai_api import *

# Create a book with a given book id
id = 123946
book = Book(id)

# Create a directory with the same name as the book title
book_dir = book.name
if not os.path.exists(book_dir):
	os.makedirs(book_dir)

# Save all the pages of the book
book.SaveAllImages(book_dir)
```