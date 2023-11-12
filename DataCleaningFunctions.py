import pandas as pd
import re
import unicodedata
import requests
from bs4 import BeautifulSoup

class DataCollection:    
    def collect_movies_artist_data(self, genre: str, year:str, sub_years:list) -> pd.DataFrame :

        titles = []
        titles_refs = []
        directors = []
        casts = []
        countries = []
        all_years = []
        genres = []

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
                    
                    titles.append(title)
                    directors.append(director)
                    casts.append(cast_list)
                    countries.append(country)
                    genres.append(genre)
                    all_years.append(sub_year)
                
                # Extracting href links 
                first_column = row.find('td')
                if first_column: 
                    href_link = first_column.find('a')
                    title_link = first_column.get_text(strip=True)
                    if href_link:
                        href = href_link.get('href').replace('/wiki/', '')
                    else:
                        href = ''
                    titles_refs.append((title_link, href))
        
        data = {"Title": titles,
                "Director": directors,
                "Cast": casts,
                "Country": countries,
                "Genre": genres, 
                "Year": all_years}
        
        df = pd.DataFrame(data)
        df['Hyperref'] = df['Title'].apply(lambda title: next((href for t, href in titles_refs if t == title), ''))
        return df

class DataCleaner:
    def __init__(self, dataframe):
        self.data = dataframe

    def remove_special_characters(self, name):
        """
        This function removes any special characters in the given text. 
        """
        return re.sub(r'[^\w\s]', ' ', name)

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

    def check_title_in_director(self, row):
        """
        This function check whether the director name occurs as the title. 
        """
        return row['Title'].lower() in row['Director'].lower()

    def clean_text(self, column, remove_special_charac=True, lower=True):
        if remove_special_charac:
            self.data[column] = self.data[column].apply(self.remove_special_characters)
        
        self.data[column] = self.data[column].str.replace(r'([a-z])([A-Z])', self.add_whitespace, regex=True)
        if lower: 
            self.data[column] = self.data[column].str.lower()
        self.data[column] = self.data[column].apply(self.change_special_letters)
        self.data[column] = self.data[column].str.strip()
        self.data[column] = self.data[column].str.replace(r'\s+', ' ', regex=True) # replace multiple whitespaces with one. 
    
    def clean_conditions(self):
        conditions = (
            (self.data['Cast'] != '') &
            (self.data['Title'] != 'citation needed') &
            (self.data['Title'] != 'Kevin VanHook') &
            (self.data['Title'] != 'J.T. Petty') &
            (self.data['Title'] != 'Reggie Bannister michael hoffman jr')
        )
        self.data = self.data[conditions].reset_index(drop=True)
    
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
            'north america': ['united states', 'canada', 'mexico', 'honduras'],
            'united states': ['usa', 'american'],
            'asia': ['indonesia', 'japan', 'taiwan', 'hong kong', 'china', 'south korea', 'myanmar', 'india', 'israel', 'jordan', 'qatar', 'japan', 'thailand', 'singapore', 
                    'malaysia', 'kazakhstan', 'vietnam', 'pakistan', 'philippines', 'bangladesh', 'bhutan', 'cambodia', 'laos', 'brunei', 'timor-leste', 'mongolia', 
                    'tajikistan', 'kyrgyzstan', 'turkmenistan', 'uzbekistan', 'kazakhstan', 'nepal'],
            'europe': ['italy', 'germany', 'france', 'norway', 'sweden', 'ireland', 'new zealand', 'netherlands', 'denmark', 'united kingdom', 'spain', 'belgium', 'poland', 
                    'czech republic', 'russia', 'austria', 'switzerland', 'iceland', 'greece', 'romania', 'serbia', 'turkey', 'luxembourg', 'portugal', 'malta', 
                    'bulgaria', 'ireland', 'croatia', 'slovenia', 'slovakia', 'latvia', 'estonia', 'hungary', 'belarus', 'lithuania', 'macedonia', 'monaco', 
                        'armenia', 'kazakhstan', 'poland', 'estonia', 'hungary', 'lithuania', 'slovenia', 'slovakia', 'estonia'],
            #'oceania': ['australia', 'new zealand', 'marshall islands','tonga','french republic', ''guam'],
            'south america': ['argentina', 'chile', 'peru', 'brazil', 'colombia', 'ecuador', 'french guiana', 'trinidad and tobago', 'venezuela', 'guyana', 'suriname']}

        def inner_map_country_to_continent(country):
            if country_counts.get(country, 0) < 45:
                for continent, countries in continent_mapping.items():
                    if country in countries:
                        return continent
                return "other"
            return country

        self.data['Country'] = self.data['Country'].apply(inner_map_country_to_continent)

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
    
    def remove_incorrect_entries(self):
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

    def differentiate_same_title(self):
        different_directors = self.data[self.data.duplicated(subset=['Title'], keep=False) &
                                        self.data.groupby(['Title'])['Director'].transform('nunique').ne(1)]
        for index, row in different_directors.iterrows():
            self.data.loc[index, 'Title'] = row['Title'] + ' ' + row['Director']
        self.data = self.data.reset_index(drop=True)

    def map_genres(self):
        # Define your specific genre combinations and their new names
        genre_combinations = {
                            ('horror',): 'horror',
                            ('comedy',): 'comedy',
                            ('action',): 'action',
                            ('thriller',): 'thriller',
                            ('science_fiction',): 'science_fiction',
                            ('adventure',): 'adventure',
                            ('fantasy',): 'fantasy',
                            ('action', 'science_fiction'): 'action-science_fiction',
                            ('action', 'thriller'): 'action-thriller',
                            ('action', 'comedy'): 'action-comedy',
                            ('adventure', 'fantasy'): 'adventure-fantasy',
                            ('comedy', 'horror'): 'comedy-horror',
                            ('comedy', 'fantasy'): 'comedy-fantasy',
                            ('horror', 'science_fiction'): 'horror-science_fiction',
                            ('horror', 'thriller'): 'horror-thriller',
                            ('adventure', 'science_fiction'): 'adventure-science_fiction',
                            ('action', 'adventure'): 'action-adventure',
                            ('action', 'adventure', 'science_fiction'): 'action-adventure-science_fiction',
                            ('adventure', 'comedy'): 'adventure-comedy'}

        # Group by title and apply a set to the 'Genre' column
        title_genres = self.data.groupby('Title')['Genre'].apply(set).reset_index()

        # Convert the set of genres to a sorted tuple
        title_genres['genre_combination'] = title_genres['Genre'].apply(lambda x: tuple(sorted(x)))

        # Map the genre combinations to the desired string or 'other'
        title_genres['Genre'] = title_genres['genre_combination'].apply(
            lambda genre_tuple: genre_combinations.get(genre_tuple, 'other'))

        # Map titles to their new genre
        title_to_new_genre = pd.Series(title_genres['Genre'].values, index=title_genres['Title']).to_dict()
        self.data['Genre'] = self.data['Title'].map(title_to_new_genre)
    
    def remove_movies(self):
        # Define movies to remove
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

    def clean_cast(self): 
        # Identifying rows with the longest 'Cast' for each 'Title'
        different_cast = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                self.data.groupby(['Title'])['Cast'].transform('nunique').ne(1)]
        max_length_indices = different_cast.groupby('Title')['Cast'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_cast.loc[max_length_indices]

        # Updating the DataFrame
        self.data = self.data[~self.data['Title'].isin(different_cast['Title'])]
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)
    
    def clean_whitespace(df, column_name):
        """
        Clean unnecessary whitespace in the specified column of a DataFrame.  
        """
        # Remove leading and trailing whitespace
        df[column_name] = df[column_name].str.strip()

        # Remove extra spaces between words (uncomment the next line if needed)
        df[column_name] = df[column_name].apply(lambda x: ' '.join(x.split()))
        return df

    def clean_hyperef(self): 
        # Identifying rows with the longest 'Hyperref' for each 'Title'
        different_hyperef = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                    self.data.groupby(['Title'])['Hyperref'].transform('nunique').ne(1)]
        max_length_indices = different_hyperef.groupby('Title')['Hyperref'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_hyperef.loc[max_length_indices]

        # Updating the DataFrame
        self.data = self.data[~self.data['Title'].isin(different_hyperef['Title'])]
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)
    
    def clean_country(self): 
        # # Identifying rows with the longest 'Country' for each 'Title'
        different_country = self.data[self.data.duplicated(subset=['Title'], keep=False) & 
                                     self.data.groupby(['Title'])['Country'].transform('nunique').ne(1)]
        # max_length_indices = different_country.groupby('Title')['Country'].apply(lambda x: x.str.len().idxmax())
        # rows_to_keep = different_country.loc[max_length_indices]

        # # Updating the DataFrame
        # self.data = self.data[~self.data['Title'].isin(different_country['Title'])]
        # self.data = self.data.append(rows_to_keep).reset_index(drop=True)
        # Identify titles that only have 'other' as the country 
        only_other_country = self.data.groupby('Title').filter(lambda x: (x['Country'] == 'other').all())
        # Remove rows with 'other' country, except those identified above
        different_country = different_country[~((different_country['Country'] == 'other') & 
                                                ~different_country['Title'].isin(only_other_country['Title']))]
        # Identify the row with the longest country name for each title
        max_length_indices = different_country.groupby('Title')['Country'].apply(lambda x: x.str.len().idxmax())
        rows_to_keep = different_country.loc[max_length_indices]
        # Update the original DataFrame
        # First, remove all rows with the titles that have duplicates in different_country
        self.data = self.data[~self.data['Title'].isin(different_country['Title'])]
        # Then, append the rows to keep to the filtered DataFrame
        self.data = self.data.append(rows_to_keep).reset_index(drop=True)

    def drop_duplicates(self): 
        self.data = self.data.drop_duplicates(keep='first')

    def clean_columns(self):
        # Clean specific columns
        self.clean_text('Director')
        self.clean_text('Title', lower=False)
        self.clean_text('Cast', remove_special_charac=False)
        self.clean_text('Country')

        # Remove rows where Title appears in Director
        self.data = self.data[~self.data.apply(self.check_title_in_director, axis=1)]
        self.data = self.data.reset_index(drop=True)
        self.clean_conditions()
        self.unique_country_combinations()
        self.map_country_to_continent()
        self.consolidate_directors()
        self.remove_incorrect_entries()
        self.differentiate_same_title()
        self.map_genres()
        self.remove_movies()
        self.clean_cast()
        self.clean_hyperef()
        self.drop_duplicates()
        self.clean_country()



class DataProcesser:    
    def split_cast(self, data):
        data['Cast'] = data['Cast'].str.split(',')
        data = data.explode('Cast').reset_index(drop=True)
        data['Cast'] = data['Cast'].str.lower()
        
        conditions = (
            (data['Cast'] != '') &
            (data['Cast'] != ' '))
        data = data[conditions].reset_index(drop=True)
        return data
    
    def clean_whitespace(self, df, column_name):
        """
        Clean unnecessary whitespace in the specified column of a DataFrame.
        """
        # Remove leading and trailing whitespace
        df[column_name] = df[column_name].str.strip()

        # Remove extra spaces between words (uncomment the next line if needed)
        df[column_name] = df[column_name].apply(lambda x: ' '.join(x.split()))
        return df

    
    def get_artist_collaboration(self, data): 
        unique_cast = data.groupby('Cast')['Title'].agg(list).reset_index()
        unique_cast = unique_cast.rename(columns={'Title': 'Titles'})

        artist_connections = {}
        for index, row in data.iterrows():
            current_artist = row['Cast']
            other_artists = data[data['Title'] == row['Title']]['Cast'].tolist()
            other_artists.remove(current_artist)
            
            if current_artist in artist_connections:
                artist_connections[current_artist].extend(other_artists)
            else:
                artist_connections[current_artist] = other_artists

        # Remove duplicates in the "connected" list
        #for artist, connections in artist_connections.items():
        #    artist_connections[artist] = list(set(connections))

        artist_connections_df = pd.DataFrame(list(artist_connections.items()), columns=['Cast', 'connected'])

        artist_connections_df['connected_count'] = artist_connections_df['connected'].apply(len)
        artist_collaboration_df = unique_cast.merge(artist_connections_df, on='Cast')
        return artist_collaboration_df






