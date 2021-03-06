from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from DataDefs import *
import mysql.connector
import time

# MYSQL_USER = "adm"
# MYSQL_PASSWORD = "circulately"
# MYSQL_HOST = "trackripple.clbystynrx1v.us-west-2.rds.amazonaws.com"
# MYSQL_DB = "trackrippledb"
# PERSIST_DB = False

MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_HOST = "localhost"
MYSQL_DB = "trackrippledb"
PERSIST_DB = True

STATS_TOTAL_BLOGS = 0
STATS_NUM_BLOGS = 0
STATS_NUM_BLOGS_WITHOUT_SC = 0
STATS_NUM_BLOGS_WITHOUT_GENRES = 0
STATS_NUM_BLOGS_WITHOUT_FOLLOWERS = 0
STATS_AVG_SONG_COUNT = 0
STATS_AVG_GENRE_COUNT = 0
STATS_SCRAPE_FAILURES = 0

NUM_SONGS_PER_BLOG = 10
NUM_TRIES = 50

BLOG_NAME_IGNORE_CHARS = len("Latest Posts from ")

def db_connect():
    return mysql.connector.connect(user = MYSQL_USER,
                                   password = MYSQL_PASSWORD,
                                   host = MYSQL_HOST,
                                   database = MYSQL_DB)

def db_disconnect(cnx):
    cnx.close()


def scrape_country_url(url):
 
    # Load WebDriver and navigate to the page url.
    # This will open a browser window.
    driver = webdriver.Firefox()
    driver.get(url)
     
    urls = []
 
    # First click on More Blogs button to launch infinite scroll 
    # and then scroll to the end of the table by sending Page Down keypresses to
    # the browser window.
    try:
        driver.find_element_by_id('more-blog-scroll').click()
    except:
        pass

    i = 0
    while i < 100:
        # Find the first element on the page, so we can scroll down using the
        # element object's send_keys() method
        elem = driver.find_element_by_tag_name('a')
        elem.send_keys(Keys.PAGE_DOWN)
        i += 1
        
    # Once the whole table has loaded, grab all the visible links.    
    blog_divs = driver.find_elements_by_class_name('directory-blog')
    for blog in blog_divs:
        link = blog.find_element_by_xpath('.//a')
        urls.append(link.get_attribute('href'))
         
    driver.quit()
           
    return urls

def scrape_countries():
    driver = webdriver.Firefox()
    driver.get('http://hypem.com/blogs')
     
    urls = []
    
    country_containers = driver.find_elements_by_id('directory-countries')
    
    for tag in country_containers:
        links = tag.find_elements_by_xpath('.//li/a')
        for link in links:
            urls.append(link.get_attribute('href'))
        
    driver.quit()

    return urls


def scrape_each_blog(url):
    global STATS_NUM_BLOGS
    global STATS_NUM_BLOGS_WITHOUT_SC
    global STATS_NUM_BLOGS_WITHOUT_GENRES
    global STATS_NUM_BLOGS_WITHOUT_FOLLOWERS

    driver = webdriver.Firefox()
    driver.get(url)

    # blog link
    try:
        blog_link = driver.find_elements_by_class_name('visit-blog')[0].find_element_by_xpath('.//a').get_attribute('href')
        blog_name = driver.find_elements_by_id('message')[0].find_element_by_xpath('.//h1').text
        blog_name = blog_name[BLOG_NAME_IGNORE_CHARS:]

        # get blog genres
        genres_list = []
        try:
            genres_ul = driver.find_element_by_css_selector(".tags.small")
            for tl in genres_ul.find_elements_by_tag_name('li'):
                genres_list.append(tl.text)
        except:
            STATS_NUM_BLOGS_WITHOUT_GENRES = STATS_NUM_BLOGS_WITHOUT_GENRES + 1

        track_num = -1
        followers_num = -1
        try:
            big_nums =  driver.find_elements_by_xpath("//span[@class='big-num']")
            # tracks
            track_num = big_nums[0].text

            # followers
            followers_num = big_nums[1].text
        except:
            STATS_NUM_BLOGS_WITHOUT_FOLLOWERS = STATS_NUM_BLOGS_WITHOUT_FOLLOWERS + 1

        # recent soundcloud music links
        sc_links = []
        # TODO: resolve this to acutal sound cloud links
        play = driver.find_element_by_id("playerPlay").click()

        sng_cnt = 0
        num_tries = 0
        while sng_cnt < NUM_SONGS_PER_BLOG and num_tries < NUM_TRIES:
            num_tries = num_tries + 1
            try:
                hypem_sc_link = driver.find_element_by_class_name("icon-sc").get_attribute("href")
                sc_links.append(hypem_sc_link)
                sng_cnt = sng_cnt + 1
                driver.find_element_by_id("playerNext").click()
            except:
                driver.find_element_by_id("playerNext").click()
                continue

        print sng_cnt, num_tries

        if sng_cnt == 0:
            STATS_NUM_BLOGS_WITHOUT_SC = STATS_NUM_BLOGS_WITHOUT_SC + 1

        print url, "Blog number ", STATS_NUM_BLOGS, " collected ", sng_cnt, " songs"
        driver.quit()
        return (blog_link, blog_name, genres_list, track_num, followers_num, sc_links)

    except:
        return (None, None, None, None, None, None) #unauthorized


#blg_list_us = scrape_url("http://hypem.com/blogs/country/US")
#scrape_each_blog("http://hypem.com/blog/abduction+radiation/21500")


def write_blog_to_db(f_blogs, blg_id, blog_name, blog_link, track_num, followers_num):
    query = 'INSERT INTO blogs (bid, bname, burl, tracks_posted, followers) VALUES ({0}, {1}, {2}, {3}, {4})'.format(blg_id, blog_name, blog_link, track_num, followers_num)
    f_blogs.write(query+"\n")

def write_blog_genres(f_blog_genres, blog_id, genres_list):
    for g in genres_list:
        if len(g) != 0:
            query = 'INSERT INTO blog_genres (bid, gname) VALUES ({0}, {1})'.format(blog_id, g)
            #print query
            f_blog_genres.write(query + "\n")

def write_genres(f_genres, genres, genres_list):
    for g in genres_list:
        if len(g) != 0 and g not in genres :
            genres[g] = g
            query = "INSERT INTO genres (gname) VALUES ({0})".format(g)
            #print query
            f_genres.write(query+"\n")

def write_blog_songs(f_blog_songs, blog_id, ):
    pass

def hypem_sc_link_resolver(hypem_sc_links):
    sc_links = []
    driver2 = webdriver.Firefox()
    for sc in hypem_sc_links:
        try:
            driver2.get(sc)
            sc_links.append(driver2.current_url)
        except:
            driver2.close()
            return []
    driver2.close()
    return sc_links

def persist_in_text_files():

    global STATS_TOTAL_BLOGS
    global STATS_NUM_BLOGS
    global STATS_NUM_BLOGS_WITHOUT_SC
    global STATS_NUM_BLOGS_WITHOUT_FOLLOWERS
    global STATS_NUM_BLOGS_WITHOUT_GENRES
    global STATS_AVG_SONG_COUNT
    global STATS_AVG_GENRE_COUNT
    global STATS_SCRAPE_FAILURES
    global NUM_SONGS_PER_BLOG

    genres = {}

    country_wise_urls = scrape_countries()
    num_countries = len(country_wise_urls)
    failed_list = []

    f = open(DATA_DIR+COUNTRY_BLOG_LINKS, "w")
    f_list = open(DATA_DIR+COUNTRY_PAGES, "w")
    f_blg = open(DATA_DIR+BLOG_FEATURES, "w")
    f_failed_list = open(DATA_DIR+FAILED_SITES, "w")
    f_blogs = open(DATA_DIR +"blogs.sql", "w")
    f_genres = open(DATA_DIR +"genres.sql", "w")
    f_blog_genres = open(DATA_DIR + "blog_genres.sql", "w")
    #f_blog_songs = open(DATA_DIR + "blog_songs.sql", "w")

    for c_url in country_wise_urls:
        country = c_url.split("/")[-1]
        f_list.write(country+" "+c_url+"\n")

        blog_list = scrape_country_url(c_url)

        # scrape each blog_link for blog characterisitcs
        for bl in blog_list:
            STATS_TOTAL_BLOGS = STATS_TOTAL_BLOGS + 1
            # be nice .... take a break
            time.sleep(1)

            # process blog
            blg_id = bl.split("/")[-1]
            (blog_link, blog_name, genres_list, track_num, followers_num, sc_links) = scrape_each_blog(bl)
            if blog_link != None:
                # collect stats
                STATS_NUM_BLOGS = STATS_NUM_BLOGS + 1
                STATS_AVG_SONG_COUNT += len(sc_links)
                STATS_AVG_GENRE_COUNT += len(genres_list)
                # persist
                write_blog_to_db(f_blogs, blg_id, blog_name, blog_link, track_num, followers_num)
                if genres is not None:
                    write_genres(f_genres, genres, genres_list)
                    write_blog_genres(f_blog_genres, blg_id, genres_list)
                if sc_links is not None:
                    sc_links_resolved = hypem_sc_link_resolver(sc_links)
                    #write_blog_songs(f_blog_songs, blg_id, sc_links_resolved)
                f.write(country+" "+bl+"\n")
                f_blg.write(blg_id+" "+blog_link+" "+blog_name+" "+'|'.join(genres_list)+
                        " "+track_num+" "+followers_num+" "+'|'.join(sc_links)+"\n")
            else:
                print "Failed to scrape blog!!!", bl
                failed_list.append(bl)
                STATS_SCRAPE_FAILURES = STATS_SCRAPE_FAILURES + 1
                time.sleep(60)  # go away for a while ... you have been a nuisance

    # do something with failed list
    #persist them for now for processing in second phase
    f_failed_list.write('|'.join(failed_list))

    print  "FINISHED SCRAPING ... PRINTING STATS"
    print  "STATS_NUM_BLOGS ", STATS_TOTAL_BLOGS
    print  "STATS_BLOGS_PER_COUNTRY ", (STATS_NUM_BLOGS/len(num_countries))
    print  "STATS_NUM_BLOGS_WITHOUT_SC ", STATS_NUM_BLOGS_WITHOUT_SC
    print  "STATS_NUM_BLOGS_WITHOUT_FOLLOWERS ", STATS_NUM_BLOGS_WITHOUT_FOLLOWERS
    print  "STATS_NUM_BLOGS_WITHOUT_GENRES ", STATS_NUM_BLOGS_WITHOUT_GENRES
    print  "STATS_AVG_SONG_COUNT_PER_BLOG ", (STATS_AVG_SONG_COUNT/STATS_NUM_BLOGS)
    print  "STATS_AVG_GENRE_COUNT_PER_BLOG ", (STATS_AVG_GENRE_COUNT/STATS_NUM_BLOGS)
    print  "STATS_SCRAPE_FAILURES", STATS_SCRAPE_FAILURES

    f.close()
    f_list.close()
    f_blg.close()
    f_failed_list.close()
    f_blogs.close()
    f_genres.close()
    f_blog_genres.close()
    #f_blog_song.close()


if __name__ == "__main__":
    persist_in_text_files()
    #write_blog_to_db(cnx, 11, "blah" , "blah", 1, 1)
    #(blog_link, blog_name, genres_list, track_num, followers_num, sc_links) = scrape_each_blog("http://hypem.com/blog/consequence+of+sound/4436")
    #print hypem_sc_link_resolver(sc_links)

