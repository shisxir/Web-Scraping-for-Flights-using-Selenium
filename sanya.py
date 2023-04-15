

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape(origin, destination, startdate, days, requests):

    global results 

    enddate = datetime.strptime(startdate, '%Y-%m-%d').date() + timedelta(days)
    enddate = enddate.strftime('%Y-%m-%d')

    #url = "https://www.kayak.com/flights/" + origin + "-" + destination + "/" + startdate + "/" + enddate + "?sort=bestflight_a&fs=stops=0"
    url = "https://www.kayak.com/flights/"
    print("\n" + url)
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    time.sleep(6)

    origin_field = driver.find_element("xpath",'/html/body/div[2]/div[1]/main/div[1]/div[1]/div/div[1]/div/div/section[2]/div/div/div/div/div/div[1]/div[2]/div/div[1]/div/div/input')
    origin_field.clear()
    origin_field.send_keys(origin)
    time.sleep(2)
    origin_field.send_keys(Keys.ENTER)
    #origin_field_dropdown = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[7]/div/div[3]/div/div/div[2]/div/div[2]/div/ul/li/div")))
    #origin_field_dropdown = driver.find_element('/html/body/div[7]/div/div[3]/div/div/div[2]/div/div[2]/div/ul/li/div/div[3]/span/span/input')
    #origin_field_dropdown.click()

    destination_field = driver.find_element("xpath",'/html/body/div[2]/div[1]/main/div[1]/div[1]/div/div[1]/div/div/section[2]/div/div/div/div/div/div[1]/div[2]/div/div[3]/div/div/input')
    destination_field.send_keys(destination)
    time.sleep(2)
    origin_field.send_keys(Keys.ENTER)

    doRandomClick = driver.find_element("xpath", '/html/body/div[2]/div[1]/main/div[1]/div[1]/div/div[1]/div/div/section[1]')
    doRandomClick.click()

    search_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/main/div[1]/div[1]/div/div[1]/div/div/section[2]/div/div/div/div/div/div[1]/div[2]/div/div[5]/button"))
    )
    search_button.click()


    #chrome_options = webdriver.ChromeOptions()
    #agents = ["Firefox/66.0.3","Chrome/73.0.3683.68","Edge/16.16299"]
    #print("User agent: " + agents[(requests%len(agents))])
    #chrome_options.add_argument('--user-agent=' + agents[(requests%len(agents))] + '"')
    #chrome_options.add_experimental_option('useAutomationExtension', False)

    #driver = webdriver.Chrome(options=chrome_options, desired_capabilities=chrome_options.to_capabilities())
    #driver.implicitly_wait(20)
    #driver.get(url)

    #Check if Kayak thinks that we're a bot
    #time.sleep(5)
    soup=BeautifulSoup(driver.page_source, 'lxml')

    if soup.find_all('p')[0].getText() == "Please confirm that you are a real KAYAK user.":
        print("Kayak thinks I'm a bot, which I am ... so let's wait a bit and try again")
        driver.close()
        time.sleep(20)
        print("FAILURE")
        return "failure"

    time.sleep(20) #wait 20sec for the page to load

    soup=BeautifulSoup(driver.page_source, 'lxml')

    #get the arrival and departure times
    deptimes = soup.find_all('span', attrs={'class': 'depart-time base-time'})
    arrtimes = soup.find_all('span', attrs={'class': 'arrival-time base-time'})
    meridies = soup.find_all('span', attrs={'class': 'time-meridiem meridiem'})

    deptime = []
    for div in deptimes:
        deptime.append(div.getText()[:-1])

    arrtime = []
    for div in arrtimes:
        arrtime.append(div.getText()[:-1])

    meridiem = []
    for div in meridies:
        meridiem.append(div.getText())

    deptime = np.asarray(deptime)
    deptime = deptime.reshape(int(len(deptime)/2), 2)

    arrtime = np.asarray(arrtime)
    arrtime = arrtime.reshape(int(len(arrtime)/2), 2)

    meridiem = np.asarray(meridiem)
    meridiem = meridiem.reshape(int(len(meridiem)/4), 4)

    #Get the price
    regex = re.compile('Common-Booking-MultiBookProvider (.*)multi-row Theme-featured-large(.*)')
    price_list = soup.find_all('div', attrs={'class': regex})

    price = []
    for div in price_list:
        price.append(int(div.getText().split('\n')[3][1:-1]))

    df = pd.DataFrame({"origin" : origin,
                       "destination" : destination,
                       "startdate" : startdate,
                       "enddate" : enddate,
                       "price": price,
                       "currency": "USD",
                       "deptime_o": [m+str(n) for m,n in zip(deptime[:,0],meridiem[:,0])],
                       "arrtime_d": [m+str(n) for m,n in zip(arrtime[:,0],meridiem[:,1])],
                       "deptime_d": [m+str(n) for m,n in zip(deptime[:,1],meridiem[:,2])],
                       "arrtime_o": [m+str(n) for m,n in zip(arrtime[:,1],meridiem[:,3])]
                       })

    results = pd.concat([results, df], sort=False)

    driver.close() #close the browser

    time.sleep(15) #wait 15sec until the next request
    print(df)
    print("SUCCESS")
    return "success"

#Create a dataframe
results = pd.DataFrame(columns=['origin','destination','startdate','enddate','deptime_o','arrtime_d','deptime_d','arrtime_o','currency','price'])

requests = 0

destinations = ['MXP']
startdates = ['2019-09-06']

for destination in destinations:
    for startdate in startdates:
        requests = requests + 1
        while scrape('ZRH', destination, startdate, 3, requests) != "success":
            requests = requests + 1

#Find the minimum price for each destination-startdate-combination
results_agg = results.groupby(['destination','startdate'])['price'].min().reset_index().rename(columns={'min':'price'})
# Once we have specified all combinations and scraped the respective data, we can nicely visualize our results using a heatmap from seaborn

heatmap_results = pd.pivot_table(results_agg , values='price',
                     index=['destination'],
                     columns='startdate')


airlines = pd.read_csv("/Users/shishirshrivastava/Downloads/airline.csv")
print(airlines)

