import pandas as pd
import re
import unicodedata
import requests
from bs4 import BeautifulSoup

class DataCollection:    
    def collect_movies_artist_data(self, genre: str, year:str, sub_years:list) -> pd.DataFrame:
        titles = []
        directors = []
        casts = []
        countries = []
        all_years = []
        genres = []
        link_refs = []

        # Defining the url. Notice that it is different for the genre horror. 
        if genre == 'horror':
            url = f"https://en.wikipedia.org/wiki/List_of_horror_films_of_{year}"
            sub_years = [year]
        else: 
            url = f"https://en.wikipedia.org/wiki/List_of_{genre}_films_of_the_{year}"

        # Get data using BeautifulSoup and HTML
        wiki_page = requests.get(url)
        soup = BeautifulSoup(wiki_page.text, 'html.parser')
        # Since the movies and artists are stored in tables, we use BeautifulSoup to find all tables in the wiki page
        all_tables = soup.find_all('table', {'class':'wikitable'})

        # The table is divided into subtables for each subyear of year degree.         
        for sub_year_idx, sub_year in enumerate(sub_years):
            for row in all_tables[sub_year_idx].find_all('tr'): 
                columns = row.find_all('td')

                # Extracting the subyear of the tables that are merged and not divided into subtables. 
                if (genre == 'thriller') or (genre == 'fantasy') or (genre=='science_fiction'): 
                    if (len(columns)!=0): 
                        if (re.search(r"2\d{3}\n", columns[0].text)):
                            sub_year = columns[0].text[:4]

                if len(columns) >= 4:
                    if genre == 'horror' and not (sub_year == '2020' or sub_year == '2021' or sub_year == '2022' or sub_year == '2019'):
                        try: 
                            title = row.find('a').get_text(strip=True)
                        except: 
                            title = row.find('i').get_text(strip=True)
                        director = columns[0].get_text(strip=True)
                        cast_list = columns[1].get_text(strip=True)
                        country = columns[2].get_text(strip=True)
                    elif genre == 'comedy' and sub_year=='2007':       
                        title = row.find('a').get_text(strip=True)
                        director = columns[0].get_text(strip=True)
                        cast_list = columns[1].get_text(strip=True)
                        country = columns[2].get_text(strip=True)
                    else: 
                        title = columns[0].get_text(strip=True)
                        director = columns[1].get_text(strip=True)
                        cast_list = columns[2].get_text(strip=True)
                        country = columns[3].get_text(strip=True)

                    # Getting hyperlinks to plots of movie
                    if genre == 'horror' and not (sub_year == '2020' or sub_year == '2021' or sub_year == '2022' or sub_year == '2019'):
                        first_column = row.find('th')
                    else:
                        first_column = row.find('td')

                    if first_column: 
                        href_link = first_column.find('a')
                        if href_link:
                            href = href_link.get('href').replace('/wiki/', '')
                        else:
                            href = ''
                    else: 
                        href = ''
            
                    titles.append(title)
                    directors.append(director)
                    casts.append(cast_list)
                    countries.append(country)
                    genres.append(genre)
                    all_years.append(sub_year)
                    link_refs.append(href)
        
        data = {"Title": titles,
                "Director": directors,
                "Cast": casts,
                "Country": countries,
                "Genre": genres, 
                "Year": all_years, 
                "Hyperref": link_refs}
        
        df = pd.DataFrame(data)
        return df

class DataCleaning:
    def __init__(self, dataframe):
        self.data = dataframe
    
    def clean_text_title_column(self, text):
        # Remove text within square brackets and parentheses
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        # Replace 
        text = text.replace('!', '')
        text = text.replace('.', '')
        return text

    def clean_text_cast_column(self, text):
        # Remove text within square brackets and parentheses
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        # Replace 
        text = text.replace('|', '')
        text = text.replace('’', "'")
        text = text.replace('.', '')
        # Remove text within double and single quotes
        text = re.sub(r"\".*?\"", '', text)
        text = re.sub(r"'.*?'", '', text)    
        return text
    
    def clean_text_director_column(self, text):
        # Remove text within square brackets and parentheses
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        # Replace + and & with a comma
        text = text.replace('+', ',')
        text = text.replace('&', ',')
        text = text.replace('-', ' ')
        text = text.replace('—', ' ')
        text = text.replace('.', '')
        # Remove text within double and single quotes
        text = re.sub(r"\".*?\"", '', text)
        text = re.sub(r"'.*?'", '', text)    
        return text
    
    def clean_text_country_column(self, text):
        # Remove text within square brackets and parentheses
        text = re.sub(r'\[.*?\]', '', text)
        # Replace 
        text = text.replace('-', ',')
        text = text.replace('<', "")
        text = text.replace('.', '')
        text = text.replace('\{', '')
        return text
    
    def clean_hyperef_column(self): 
        # Identifying rows with the longest 'Hyperref' for each 'Title'
        different_hyperef = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                    self.data.groupby(['Title'])['Hyperref'].transform('nunique').ne(1)]
        max_length_indices = different_hyperef.groupby('Title')['Hyperref'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_hyperef.loc[max_length_indices]

        # Updating the DataFrame
        self.data = self.data[~self.data['Title'].isin(different_hyperef['Title'])]
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)
    
    def add_whitespace(self, match):
        """
        This function add whitespace between concatenated words in a string where there is a lowercase letter followed immediately by an uppercase letter.
        """
        return match.group(1) + ' ' + match.group(2)

    def change_special_letters(self, text):
        """
        This function changes speciel letters with normal letters. 
        """
        normalized_text = unicodedata.normalize('NFD', text)
        return normalized_text.encode('ascii', 'ignore').decode('ascii')

    def clean_text(self, column, lower=True):
        self.data[column] = self.data[column].str.replace(r'([a-z])([A-Z])', self.add_whitespace, regex=True) # adds space between concatenated words
        self.data[column] = self.data[column].apply(self.change_special_letters) # replace speciel letters with normal letters
        self.data[column] = self.data[column].str.strip()
        self.data[column] = self.data[column].str.replace(r'\s+', ' ', regex=True) # removes duplicated whitespaces
        if lower: 
            self.data[column] = self.data[column].str.lower() # lowercase for all besides titles and cast 
    
    def drop_rows_conditions(self):
        conditions = (
            (self.data['Cast'] != '') &
            (self.data['Title'] != '') &
            (self.data['Cast'] != 'canada') & 
            (self.data['Title'] != 'citation needed') &
            (self.data['Title'] != 'Kevin VanHook') &
            (self.data['Title'] != 'J.T. Petty') &
            (self.data['Title'] != 'Reggie Bannister michael hoffman jr'))
        
        self.data = self.data[conditions].reset_index(drop=True)

        # These titles with the corresponding director is wrong entries. 
        incorrect_entries = [
            ('Hot Tub Time Machine', 'sean anders john morris'),
            ('The Matrix Reloaded', 'the wachowskis nb 9'),
            ('The Matrix Revolutions', 'the wachowskis nb 10'),
            ('Jade Warrior', 'tommi eronen'),
            ('The Bleeding', 'charles picerni'),
            ('The Huntsman: Winter\'s War', 'frank darabont'),
            ('Stowaway', 'adam lipsius'), 
            ('World War Z', 'chris la martina')]
        
        for title, wrong_director in incorrect_entries:
            idx_to_remove = self.data[(self.data['Title'] == title) & 
                                        (self.data['Director'].str.lower() == wrong_director.lower())].index
            self.data = self.data.drop(idx_to_remove)

        # Define movies to remove due to wrong year
        movies_to_remove_year = {
                        'Run Sweetheart Run': "2022",
                        'The Black Phone': "2022",
                        'Bhool Bhulaiyaa 2': "2021",
                        'Apartment 143': "2012",
                        'Underworld: Blood Wars': "2017", 
                        'Bloody Bloody Bible Camp': '2012', 
                        'Flash Point': '2006', 
                        'Kingsman: The Secret Service': '2015', 
                        'Battle Royale': '2001',
                        'Smokin\' Aces': '2007',
                        'Tokyo Gore Police': '2007',
                        'Sky Captain and the World of Tomorrow': '2003',
                        'Decoys': '2003', 
                        'How to Talk to Girls at Parties': '2018',
                        'Monsters: Dark Continent': '2014', 
                        'Kingsman: The Secret Service': '2015', 
                        'Donkey Punch': '2007', 
                        'Manborg': '2010', 
                        'Army of Frankensteins': '2014',
                        'Growth':'2009', 
                        'Universal Soldier: Regeneration': '2010',
                        'Army of Frankensteins': '2014',
                        'BloodRayne': '2006',
                        '300': '2007', 
                        'M3GAN': '2023', 
                        'Excision': '2008', 
                        'Color Out of Space': '2020',
                        'Faust: Love of the Damned': '2001',
                        'Bunshinsaba': '2012',
                        'An American Haunting': '2006',
                        'The Gingerdead Man': '2006', 
                        'Big Bad Wolf': '2007',
                        'Hurt': '2008',
                        'Strigoi': '2009',
                        'Seventh Son': '2015', 
                        'The Shape of Water': '2018', 
                        'Beowulf & Grendel': '2006', 
                        'Dirty Deeds': '2002', 
                        'Beowulf Grendel': '2006'}
        
        movies_to_remove_hyperref = {'The Beach': 'The_Beach_(2000_film)', 
                                        'Edge of Tomorrow': 'Edge_of_Tomorrow_(film)', 
                                        'The Medallion': 'The_Medallion_(film)'}
            
        # Create a mask for all movies to be removed at once
        mask_year = self.data.apply(lambda x: (x['Title'], x['Year']) in movies_to_remove_year.items(), axis=1)
        self.data = self.data[~mask_year].reset_index(drop=True)

        mask_hyperref = self.data.apply(lambda x: (x['Title'], x['Hyperref']) in movies_to_remove_hyperref.items(), axis=1)
        self.data = self.data[~mask_hyperref].reset_index(drop=True)
        
    def consolidate_directors(self):
        def inner_consolidate_directors(group):
                # Find the longest director name
            longest_director = max(group, key=len)
            # Split the longest name into a set of words for easy comparison
            longest_director_words = set(longest_director.lower().split())

            # Function to check if any part of a shorter name is in the longest name
            def is_subname_any(shorter, longer_words):
                shorter_words = set(shorter.lower().split())
                # Check if any word from the shorter name is in the longer name
                return any(word in longer_words for word in shorter_words)

            # Consolidate director names
            group = [longest_director if is_subname_any(d, longest_director_words) else d for d in group]
            return group
        self.data['Director'] = self.data.groupby('Title')['Director'].transform(inner_consolidate_directors)
    
    def differentiate_same_title(self):
        different_directors = self.data[self.data.duplicated(subset=['Title'], keep=False) &
                                        self.data.groupby(['Title'])['Director'].transform('nunique').ne(1)]
        for index, row in different_directors.iterrows():
            self.data.loc[index, 'Title'] = row['Title'] + ' ' + row['Director']
        self.data = self.data.reset_index(drop=True)
    
    def clean_cast(self): 
        # Identifying rows with the longest 'Cast' for each 'Title'
        different_cast = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                self.data.groupby(['Title'])['Cast'].transform('nunique').ne(1)]
        max_length_indices = different_cast.groupby('Title')['Cast'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_cast.loc[max_length_indices]

        # Updating the DataFrame
        self.data = self.data[~self.data['Title'].isin(different_cast['Title'])]
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)
    
    def data_clean_genres(self):
        # Define your specific genre combinations and their new names
        genre_combinations = {
                            ('horror',): 'Horror',
                            ('comedy',): 'Comedy',
                            ('action',): 'Action',
                            ('thriller',): 'Thriller',
                            ('science_fiction',): 'Science Fiction',
                            ('adventure',): 'Adventure',
                            ('fantasy',): 'Fantasy',
                            ('action', 'science_fiction'): 'Science Fiction',
                            ('action', 'thriller'): 'Action',
                            ('action', 'comedy'): 'Action',
                            ('adventure', 'fantasy'): 'Fantasy',
                            ('comedy', 'horror'): 'Horror',
                            ('comedy', 'fantasy'): 'Fantasy',
                            ('horror', 'science_fiction'): 'Science Fiction',
                            ('horror', 'thriller'): 'Horror',
                            ('adventure', 'science_fiction'): 'Science Fiction',
                            ('action', 'adventure'): 'Action',
                            ('action', 'adventure', 'science_fiction'): 'Science Fiction',
                            ('adventure', 'comedy'): 'Comedy'}

        # Group by title and apply a set to the 'Genre' column
        title_genres = self.data.groupby('Title')['Genre'].apply(set).reset_index()

        # Convert the set of genres to a sorted tuple
        title_genres['genre_combination'] = title_genres['Genre'].apply(lambda x: tuple(sorted(x)))

        # Map the genre combinations to the desired string or 'other'
        title_genres['Genre'] = title_genres['genre_combination'].apply(
            lambda genre_tuple: genre_combinations.get(genre_tuple, 'Mix'))

        # Map titles to their new genre
        title_to_new_genre = pd.Series(title_genres['Genre'].values, index=title_genres['Title']).to_dict()
        self.data['Genre'] = self.data['Title'].map(title_to_new_genre)
    
    def unique_country_combinations(self):
        unique_combinations = {}
        unique_country_combinations = []
        for index, row in self.data.iterrows():
            country_combination = ' '.join(sorted(row['Country'].split()))
            if country_combination not in unique_combinations:
                unique_combinations[country_combination] = row['Country']
                unique_country_combinations.append(country_combination)
            else:
                first_occurrence_index = unique_country_combinations.index(country_combination)
                unique_country_combinations.append(unique_country_combinations[first_occurrence_index])
        self.data['Country'] = [unique_combinations[combination] for combination in unique_country_combinations]

    def map_country_to_continent(self):
        country_counts = self.data['Country'].value_counts()
        continent_mapping = {
            'north nmerica': ['united states', 'canada', 'mexico', 'honduras'],
            'united states': ['usa', 'american'],
            'asia': ['indonesia', 'japan', 'taiwan', 'hong kong', 'china', 'south korea', 'myanmar', 'india', 'israel', 'jordan', 'qatar', 'japan', 'thailand', 'singapore', 
                    'malaysia', 'kazakhstan', 'vietnam', 'pakistan', 'philippines', 'bangladesh', 'bhutan', 'cambodia', 'laos', 'brunei', 'timor-leste', 'mongolia', 
                    'tajikistan', 'kyrgyzstan', 'turkmenistan', 'uzbekistan', 'kazakhstan', 'nepal'],
            'europe': ['italy', 'germany', 'france', 'norway', 'sweden', 'ireland', 'new zealand', 'netherlands', 'denmark', 'united kingdom', 'spain', 'belgium', 'poland', 
                    'czech republic', 'russia', 'austria', 'switzerland', 'iceland', 'greece', 'romania', 'serbia', 'turkey', 'luxembourg', 'portugal', 'malta', 
                    'bulgaria', 'ireland', 'croatia', 'slovenia', 'slovakia', 'latvia', 'estonia', 'hungary', 'belarus', 'lithuania', 'macedonia', 'monaco', 
                        'armenia', 'kazakhstan', 'poland', 'estonia', 'hungary', 'lithuania', 'slovenia', 'slovakia', 'estonia'],
            'south america': ['argentina', 'chile', 'peru', 'brazil', 'colombia', 'ecuador', 'french guiana', 'trinidad and tobago', 'venezuela', 'guyana', 'suriname']}

        def inner_map_country_to_continent(country):
            if country_counts.get(country, 0) < 45:
                for continent, countries in continent_mapping.items():
                    if country in countries:
                        return continent
                return "mix"
            return country
        self.data['Country'] = self.data['Country'].apply(inner_map_country_to_continent)
        
    def clean_country(self): 
        # Identifying rows with the longest 'Country' for each 'Title'
        different_country = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                        self.data.groupby(['Title'])['Country'].transform('nunique').ne(1)]
        
        # Remove rows with 'other' country, except those identified above
        only_other_country = self.data.groupby('Title').filter(lambda x: (x['Country'] == 'other').all())
        different_country = different_country[~((different_country['Country'] == 'other') & 
                                                ~different_country['Title'].isin(only_other_country['Title']))]
        
        # Identify the row with the longest country name for each title
        max_length_indices = different_country.groupby('Title')['Country'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_country.loc[max_length_indices]

        # First, remove all rows with the titles that have duplicates in different_country
        self.data = self.data[~self.data['Title'].isin(different_country['Title'])]
        
        # Then, append the rows to keep to the filtered DataFrame
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)

    def data_cleaning(self): 
        self.data['Title'] = self.data['Title'].apply(self.clean_text_title_column)
        self.clean_text('Title', lower = False)
        
        self.data['Cast'] = self.data['Cast'].apply(self.clean_text_cast_column)
        self.clean_text('Cast')
        self.drop_rows_conditions()

        self.data['Director'] = self.data['Director'].apply(self.clean_text_director_column)
        self.clean_text('Director')
        self.consolidate_directors()
        self.differentiate_same_title()

        self.clean_cast()

        self.clean_text('Genre')
        self.data_clean_genres()
        
        self.data['Country'] = self.data['Country'].apply(self.clean_text_country_column)
        self.clean_text('Country')
        self.unique_country_combinations()
        self.map_country_to_continent()
        self.clean_country()

        self.clean_hyperef_column()

        self.data = self.data.drop_duplicates(keep='first')

class GetConnectedMoviesArtist:

    def connected_movies_and_cast(self, df_movies: pd.DataFrame):
        # Create a dictionary to map each movie to its cast
        movie_cast_map = {}
        for index, row in df_movies.iterrows():
            cast_list = [cast.strip() for cast in row['Cast'].split(',')]
            movie_cast_map[row['Title']] = set(cast_list)

        # Create the desired dictionary structure
        connected_movies = {}
        for movie, casts in movie_cast_map.items():
            connections = {}
            for other_movie, other_casts in movie_cast_map.items():
                if movie != other_movie:
                    shared_casts = casts.intersection(other_casts)
                    if shared_casts:
                        connections[other_movie] = list(shared_casts)
            # Include the movie even if it has no connections
            connected_movies[movie] = connections
        return connected_movies