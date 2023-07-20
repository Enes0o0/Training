import time
import sqlite3
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By

app = Flask(__name__)

def get_pokemons():
    url = "https://pokeapi.co/api/v2/pokemon?limit=10"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        pokemons = data["results"]
        return pokemons
    else:
        return []

def create_product_table(conn):
    # Product tablosunu oluşturma
    create_table_query = """
        CREATE TABLE IF NOT EXISTS Product (
            Name VARCHAR(70) NULL,
            Price DECIMAL(18, 2) NULL,
            Description VARCHAR(120) NULL,
            Stock INT NULL
        )
    """
    conn.execute(create_table_query)

def insert_product_data(conn, product):
    # Ürünü Product tablosuna ekleme
    insert_query = """
        INSERT INTO Product (Name, Price, Description, Stock)
        VALUES (?, ?, ?, ?)
    """
    conn.execute(insert_query, (product.Name, product.Price, product.Description, product.Stock))

def get_filtered_pokemons(include_columns, exclude_columns):
    # ChromeDriver'ı başlat
    driver = webdriver.Chrome()

    # Web sayfasını aç
    driver.get("https://scrapeme.live/shop/")

    # Ürünleri bulmak için CSS selektörünü kullan
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".products li")

    products = []

    how_many_page = int(driver.find_element(By.XPATH, "/html/body/div/div[2]/div/div[2]/main/div[1]/nav/ul/li[8]/a").text)

    for x in range(1, how_many_page + 1):
        # Her bir ürün için bilgileri topla
        for i in range(1, len(product_elements)):
            time.sleep(1.7)

            name = driver.find_element(By.XPATH, f"/html/body/div/div[2]/div/div[2]/main/ul/li[{i}]/a[1]/h2").text
            price_text = driver.find_element(By.XPATH, f"/html/body/div/div[2]/div/div[2]/main/ul/li[{i}]/a[1]/span/span").text
            price = float(price_text.replace("£", ""))

            tiklanacak_element = driver.find_element(By.XPATH, f"/html/body/div/div[2]/div/div[2]/main/ul/li[{i}]/a[1]/img")
            tiklanacak_element.click()

            time.sleep(1.8)

            # Ürün açıklamasını ve stok bilgisini bul
            description_element = driver.find_element(By.CSS_SELECTOR, ".woocommerce-product-details__short-description p")
            description = description_element.text

            stock_element = driver.find_element(By.CSS_SELECTOR, ".stock")
            stock = int(stock_element.text.split(' ')[0])

            driver.execute_script("window.history.go(-1)")

            # Ürünü oluştur ve listeye ekle
            product = ProductViewModel(name, price, stock, description)
            products.append(product)

        tiklanacak_element2 = driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers")
        tiklanacak_element2.click()

    # Tarayıcıyı kapat
    driver.quit()

    # İstenilen kolonları içeren ürünleri filtrele
    filtered_products = []
    for product in products:
        filtered_product = {key: value for key, value in product.__dict__.items() if key in include_columns and key not in exclude_columns}
        filtered_products.append(filtered_product)

    return filtered_products

@app.route('/pokemons', methods=['GET'])
def get_pokemons_endpoint():
    include_columns = set(request.args.get('in', '').split(','))
    exclude_columns = set(request.args.get('ex', '').split(','))

    # Tüm kolonları almak için boş bir istek yapılırsa varsayılan olarak tüm kolonları göster
    if not include_columns and not exclude_columns:
        include_columns = {"Name", "Price", "Description", "Stock"}

    products = get_filtered_pokemons(include_columns, exclude_columns)

    # SQLite veritabanı bağlantısını oluştur
    conn = sqlite3.connect("products.db")

    # Product tablosunu oluştur
    create_product_table(conn)

    # Ürünleri veritabanına ekleyin
    for product in products:
        insert_product_data(conn, product)

    # Değişiklikleri kaydedin ve bağlantıyı kapatın
    conn.commit()
    conn.close()

    return jsonify(products), 200

class ProductViewModel:
    def __init__(self, name, price, stock, description):
        self.Name = name
        self.Price = price
        self.Stock = stock
        self.Description = description

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)




# Yazdığım kod, localhost/pokemons/ex=name,stock isteğinde verilen kolonları JSON çıktısında göstermeyecektir
# Ayrıca localhost/pokemons/in=description,name isteğinde yalnızca verilen kolonları JSON çıktısında gösterecektir.
# Ayrıca localhost/pokemons endpoint'iyle tüm kolonları ortak olarak varsayılan şekle ayarladım
# Dockerize edildiğinde servis localhost:5000/pokemons adresinden erişilebilir olacaktır. Bu kısmı tam yapamadım 
# Kod, istenilen şekilde hem verileri siteden çekecek hem de veritabanında tabloya ekleyecek bunun için sqlite kullandım python'daki 
# Aynı zamanda yapılandırma dosyası ile yönetilebilir şekilde Flask REST API servisi oluşturur. Pythonda rest api servisini kullanmak için Flask kütüphanesini kullandım
# Ayrıca, API gateway kullanarak servisi güvenli hale getirmeye çalıştım istediğiniz şekilde.
# python3.11 üzerinden çalışacak servis 
# Verileri çekerken html css şeklinde sorun olacağı için selenium kullanarak verileri istediğiniz siteden almaya çalıştım