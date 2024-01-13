import requests

from environs import Env


def main():
    url = 'https://smsc.ru/rest/send/'
    # url = 'https://www2.smsc.ru/rest/send/'
    params = {
        'login': env('SMSC_LOGIN'),
        'psw': env('SMSC_PASSWORD'),
        'phones': env('PHONES'),
        'mes': 'Сегодня будет гроза\n Сегодня будет холодно',
        'cost': 1,
        'fmt': 3,
    }
    print(params)
    response = requests.post(url, json=params)
    print(response.json())
    

if __name__ == '__main__':
    env = Env()
    env.read_env()
    
    main()
