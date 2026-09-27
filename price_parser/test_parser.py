from parser import parse_page

SAMPLE = """
<article class="product_pod">
  <p class="star-rating Three"></p>
  <h3><a href="a-light_1/index.html" title="A Light in the Attic">A Light...</a></h3>
  <div class="product_price">
    <p class="price_color">£51.77</p>
    <p class="instock availability">In stock</p>
  </div>
</article>
"""


def test_parse_page():
    items = parse_page(SAMPLE, "https://books.toscrape.com/catalogue/page-1.html")
    assert items == [{
        "title": "A Light in the Attic",
        "price": 51.77,
        "in_stock": True,
        "rating": 3,
        "url": "https://books.toscrape.com/catalogue/a-light_1/index.html",
    }]
