# Nhentai api

Yet another object-oriented nhentai api. Will multithread when downloading multiple things, such as entire books

## Example usage

```
from Nhentai_api import *

# Create a book with a given book id
id = 123946
book = Book(id)

book_dir = book.name
if not os.path.exists(book_dir):
	os.makedirs(book_dir)
        
book.SaveAllImages(book_dir)
```