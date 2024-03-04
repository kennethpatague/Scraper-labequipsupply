from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import csv
import os

headers = {
    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'Referer': 'https://labequipsupply.co.za',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'sec-ch-ua-platform': '"Windows"',
}

def product_listing():
    url = "https://labequipsupply.co.za/product-sitemap.xml"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, features='xml')

        product_lists = []
        for loc_tag in soup.find_all('loc'):
            if 'product' in loc_tag.get_text():
                product_lists.append(loc_tag.get_text())

    return product_lists

def product_scraping(product_url):
    res = requests.get(product_url, headers=headers).content.decode()
    html_content = HTMLParser(res)
    forms = html_content.css_first('form.variations_form.cart')
    title = html_content.css_first('h1')
    add_to_cart = html_content.css_first('button.single_add_to_cart_button.button.alt')

    in_stock = False
    cart = ''
    if add_to_cart:
        in_stock = True
        
        if in_stock == True:
            cart = "Yes"
        else:
            cart = "No"


    parsed_products = []
    if forms:
        p_variant = forms.attributes.get('data-product_variations')
        attrs = json.loads(p_variant)

        if not isinstance(attrs, bool):
            for attr in attrs:
                variant = attr['attributes']

                options = ["", "", "", ""]
                counter = 1
                for key, value in variant.items():
                    var_url = f'{product_url}?{key}={value.replace(" ", "+").replace(":", "%3A")}'
                    options[counter] = key.replace("attribute_", "").title() + ": " + value
                    counter += 1

                print(f"Scraping {var_url}")

                # title = attr['image']['caption']
                price = attr['display_price']

                stock_html = BeautifulSoup(attr['availability_html'], 'html.parser')
                availability = stock_html.select_one('span.stock.in-stock')
                if availability:
                    available = availability.get_text()
                else:
                    available = ""

                sku = attr['sku']
                image_url = attr['image']['url']
                option1 = options[1]
                option2 = options[2]
                option3 = options[3]
                option4 = options[3]

                product_info = {
                    "Title": title.text(),
                    "Product URL": var_url,
                    "SKU": sku,
                    "Image URL": image_url,
                    "Price": "R" + str(price),
                    "Stock": available,
                    "Available": cart,
                    "Option#1": option1
                }

                parsed_products.append(product_info)

        else:
            print(f"Check this product {product_url}")
            
    else:
        print(f"Scraping {product_url}")

        price = html_content.css_first('p').text().replace(" Incl VAT", "")
        sku = html_content.css_first('span.sku')
        image_url_element = html_content.css_first('img.wp-post-image')

        if image_url_element:
            image_url = image_url_element.attributes.get('data-src')
        else:
            image_url = ""

        availability = html_content.css_first('span.stock.in-stock')
        if availability:
            available = availability.text()
        else:
            available = ""

        product_info = {
            "Title": title.text(),
            "Product URL": product_url,
            "SKU": sku.text() if sku else "",
            "Image URL": image_url,
            "Price": price,
            "Stock": available,
            "Available": cart,
            'Option#1': "",
        }
        parsed_products.append(product_info)

    return parsed_products

def result(parsed_products, write_header=True):
    if not parsed_products:
        print("No product found")
        return

    with open('labequipsupply.csv', 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["Title", "Product URL", "SKU", "Image URL", "Price", "Stock", "Available", "Option#1"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header and f.tell() == 0:
            writer.writeheader()

        for product in parsed_products:
            writer.writerow(product)
        
        f.flush()

def scrape_and_write(product_url):
    scraped_products = product_scraping(product_url)
    result(scraped_products)


def main():
    try:
        listings = product_listing()
        if not listings:
            print("No product listings found.")
            return

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(scrape_and_write, url) for url in listings]
            for future in futures:
                try:
                    future.result()
                except KeyboardInterrupt:
                    print("Interrupted by user. Exiting...")
                    executor.shutdown(wait=False)
                    os._exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(1)


if __name__ == '__main__':
    main()
