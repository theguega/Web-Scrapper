import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from login import credentials
import networkx as nx
import tldextract

# Créer un graphe NetworkX
G = nx.Graph()

# URL de la page de connexion
login_url = "https://cas.utc.fr/cas/login.jsf"

# URL de la page à scraper après la connexion
target_url = "https://webapplis.utc.fr/ent/index.jsf"

# Création d'une session pour maintenir la connexion
session = requests.Session()

# Effectuer la connexion
login_response = session.get(login_url)
login_soup = BeautifulSoup(login_response.content, 'html.parser')

# Extraire les paramètres nécessaires pour la soumission du formulaire
execution_value = login_soup.find('input', {'name': 'execution'})['value']

# Préparer les données pour la soumission du formulaire
login_payload = {
    'username': credentials['username'],
    'password': credentials['password'],
    'execution': execution_value,
    '_eventId': 'submit',
    'geolocation': '',
}

# Fonction pour extraire le domaine à partir d'une URL
def extract_domain(url):
    extraction = tldextract.extract(url)
    return extraction.domain

# Fonction pour récupérer les liens d'une page avec filtrage
def get_links(page_url):
    response = session.get(page_url)

    # Traitement de la page cible
    index_page = BeautifulSoup(response.content, 'html.parser')
    links = index_page.find_all("a")
    valid_links = []

    for link in links:
        href = link.get("href")
        if href and (href[0] != "#") and ("null" not in href):
            # si le lien est relatif
            if ("http" or "https") not in link.get("href"):
                full_link = urljoin(target_url, link.get("href"))
                # Exclure les liens se terminant par ".pdf" et commençant par "mailto:"
                if not (full_link.endswith(".pdf") or full_link.startswith("mailto:") or full_link.startswith("tel:") or full_link.startswith("https://www.utc.fr")):
                    valid_links.append(full_link)
            # sinon
            else:
                # Exclure les liens se terminant par ".pdf" et commençant par "mailto:"
                if not (link.get("href").endswith(".pdf") or link.get("href").startswith("mailto:")):
                    valid_links.append(link.get("href"))
    return valid_links


# Fonction pour récupérer le titre d'une page
def get_page_title(url):
    response = session.get(url)
    page_soup = BeautifulSoup(response.content, 'html.parser')
    title_tag = page_soup.find("title")
    return title_tag.text if title_tag else "Titre non trouvé"

# Fonction pour scraper les pages en profondeur
def scrape_page(url, depth=0, source=None):
    # Vérifier si la page a déjà été visitée
    if url in visited_pages:
        return

    # Extraire le domaine de l'URL
    domain = extract_domain(url)

    # Vérifier la whitelist et la blacklist pour la compléter si besoin
    if domain in blacklist:
        return
    elif domain not in whitelist:
        print(f"Lien non reconnu : {url}")
        choice = input(f"Le domaine {domain} n'est pas dans la whitelist ni la blacklist. Ajouter en whitelist (w) ou blacklist (b)? ").lower()
        if choice == 'w':
            whitelist.append(domain)
            update_whitelist()
        elif choice == 'b':
            blacklist.append(domain)
            update_blacklist()
        else:
            print("Choix invalide. Ignoré.")
            return

    # On applique notre filtre une deuxieme fois pour les pages qui viennet d'être rajoutés
    if domain in blacklist:
        return
    
    # Ajouter la page à la liste des pages visitées
    visited_pages.add(url)
    
    links = get_links(url)

    # Affichage de la page en traitement
    title = get_page_title(url)
    print("Informations sur la page : ")
    print(f"Profondeur : from [{source}] -> [{depth}]")
    print(f"Url : [{url}]")
    print(f"Titre : [{title}]")
    print(f"Nombre de liens : [{len(links)}]\n")
    # Affichage de tous les liens présents sur la page
    for link in links:
        G.add_edge(url, link)
        print(f"    - {link}")

    print("\n\n\n------------------------\n\n\n")

    # Scraper les pages liées en profondeur si elles n'ont pas déjà été visitées
    for link in links:
        if link not in visited_pages:
            scrape_page(link, depth + 1, url)

# Initialiser l'ensemble des pages visitées
visited_pages = set()

# Soumettre le formulaire de connexion
response = session.post(login_url, data=login_payload)

# Charger la whitelist et la blacklist depuis le fichier
def load_list(filename):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        return []

whitelist_filename = 'whitelist.txt'
blacklist_filename = 'blacklist.txt'
whitelist = load_list(whitelist_filename)
blacklist = load_list(blacklist_filename)

# Fonction pour mettre à jour la whitelist dans le fichier
def update_whitelist():
    with open(whitelist_filename, 'w') as file:
        file.write('\n'.join(whitelist))

# Fonction pour mettre à jour la blacklist dans le fichier
def update_blacklist():
    with open(blacklist_filename, 'w') as file:
        file.write('\n'.join(blacklist))

# Vérifier si la connexion a réussi (vous pouvez personnaliser cette vérification en fonction du site)
if "Authentication failed" in response.text:
    print("Échec de la connexion. Vérifiez vos identifiants.")
else:
    # Scraper la page cible et ses liens en profondeur
    scrape_page(target_url, 0, "Main page")

# Exporter le graphe au format GraphML
nx.write_graphml(G, 'graph.graphml')

# Fermer la session
session.close()