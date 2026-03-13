from bs4 import BeautifulSoup
import requests

response = requests.get('https://news.ycombinator.com/news')
yc_webpage = response.text

soup = BeautifulSoup(yc_webpage, 'html.parser')

article_tag = soup.find(name="span", class_="titleline").find(name="a")

article_text = article_tag.get_text()

print(article_text)