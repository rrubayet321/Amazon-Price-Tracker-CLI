import requests
from bs4 import BeautifulSoup

URL = "https://www.afi.com/afis-100-years-100-movies/"

# This tells the website you are a real Chrome browser on a Mac
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

all_movies = soup.find_all(name="h6", class_="q_title")

#ensuring that we get the top 100 movies only

top100_movies = all_movies[:100]

#storing the movie titles in a list
movie_titles = [movie.get_text() for movie in top100_movies]
movies = movie_titles

with open("movies.txt", mode="w", encoding="utf-8") as file:
    for movie in movies:
        file.write(f"{movie}\n")

print(f"Successfully created movies.txt")
