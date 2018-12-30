def exchange_rate_previous_day(currency, value, date):
    """
    Returns currency converted to PLN according to NBP exchange rate from the previous day.

    It takes holidays and weekends into account.
    Once checked values are being cached in local database (sqlite3).

    Parameters
    ----------
    currency : str
        Currency symbol as three letter code, e.g. "USD", "EUR"
    value : float
        Numerical value amount of currency to be exchanged into PLN
    date : srt or datetime object
        Date as string (YYYY-MM-DD or DD/MM/YYYY) or datetime object

    Returns
    -------
    float
        Value exchanged into PLN

    """

    # time
    from datetime import datetime, timedelta

    # db
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, Integer, String, Float
    from sqlalchemy.orm import sessionmaker

    # online scenario
    import json
    import requests

    # PLN scenario
    if currency == "PLN":
        return value

    # get date in proper format
    if type(date) is str:
        try:
            date = datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            date = datetime.strptime(date, "%Y-%m-%d")
    elif type(date) is datetime:
        date = date

    # previous day
    date = date - timedelta(days=1)

    # database scenario
    # create database
    engine = create_engine("sqlite:///exchange-dba.sqlite", echo=False)
    Base = declarative_base()

    class Exchange_rates(Base):
        __tablename__ = "historical_exchange_rates"

        id = Column(Integer, primary_key=True)
        currency_date = Column(String)
        exchange_rate = Column(Float)

    class Holiday_dates(Base):
        __tablename__ = "dates_of_holidays"

        id = Column(Integer, primary_key=True)
        holiday_date = Column(String)

    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # check if there is a holiday that day
    try:
        db_holiday = (
            session.query(Holiday_dates)
            .filter(Holiday_dates.holiday_date == date.strftime("%Y-%m-%d"))
            .first()
        )
        if db_holiday.holiday_date == date.strftime("%Y-%m-%d"):
            return exchange_rate_previous_day(currency, value, date)
    except:
        pass

    # find FX in db
    currency_date_entry = currency + date.strftime("%Y-%m-%d")

    try:
        db_rate = (
            session.query(Exchange_rates)
            .filter(Exchange_rates.currency_date == currency_date_entry)
            .first()
        )
        return float("{:.4f}".format(db_rate.exchange_rate * value))
    except:
        pass

    # online scenario
    headers = {"Accept": "application/json"}
    api_base_url = "http://api.nbp.pl/api/exchangerates/rates/"

    api_url = "{0}A/{1}/{2}".format(api_base_url, currency, date.strftime("%Y-%m-%d"))

    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        rate = json.loads(response.content.decode("utf-8"))["rates"][0]["mid"]

        new_exchange_rate = Exchange_rates(
            currency_date=currency_date_entry, exchange_rate=rate
        )
        session.add(new_exchange_rate)
        session.commit()

        return float("{:.4f}".format(rate * value))

    new_holiday = Holiday_dates(holiday_date=date.strftime("%Y-%m-%d"))
    session.add(new_holiday)
    session.commit()

    return exchange_rate_previous_day(currency, value, date)


if __name__ == "__main__":
    # stuff only to run when not called via 'import' here
    print(exchange_rate_previous_day(currency="EUR", value=100, date="2018-12-16"))
