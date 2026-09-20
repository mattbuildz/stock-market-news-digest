from operator import ne
import pprint
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic
import requests
import os

import json

FINNHUB_KEY = os.environ["FINNHUB_API_KEY"]
SOURCE = "file"   # or "api"
#SOURCE = "api"   # or "api"



API_CLAUDE = Anthropic() #anthropic client

# Fake API response for testing chunking for free, without real API calls.
# Inactive until you swap the call below in classify_news (see the comment at response = ...).
class FakeResponse:
    content = [type("obj", (), {"text": "999|999"})()]

def fake_call(**kwargs):
    return FakeResponse()

#====================================================================================


STAGE1_SYSTEM_PROMPT = """Jesteś filtrem newsów finansowych. Dostajesz ponumerowaną listę newsów o JEDNEJ spółce (etykieta [TICKER] w każdej linii), każdy jako tytuł i opcjonalnie streszczenie po "SUMMARY:".

Twoje jedyne zadanie: dla KAŻDEGO numeru z wejścia zdecyduj KEEP albo REJECT.

REGUŁA (jedyna):
Czy w tytule LUB w streszczeniu jest konkretny, weryfikowalny fakt dotyczący analizowanej spółki — liczba, kwota, nazwane wydarzenie, konkretne działanie albo decyzja?
TAK → KEEP. NIE → REJECT.

Doprecyzowania do tej reguły (nie są osobnymi kryteriami):
1. Nie oceniaj po formie. Styl, format i ton nagłówka nic nie znaczą — clickbait, "What's Going On With X Stock", zestawienia "market movers", dramatyczna narracja ("ktoś się myli"), ton promocyjny. To informacja o tym, JAK coś napisano, nie o tym, CO jest w treści. Czytaj streszczenie do końca, zawsze.
2. Sam tytuł wystarcza. Jeśli fakt jest w tytule, to KEEP — nawet gdy streszczenie jest generyczne, promocyjne albo w ogóle o czymś innym. W tych danych streszczenia są często automatycznie doklejone i niepowiązane z tytułem; niepasujące streszczenie nie unieważnia faktu z tytułu.
3. Spółka nie musi być główną bohaterką. Może być wymieniona jako druga, na końcu zdania, obok większej lub bardziej znanej firmy. Jeśli fakt jej dotyczy (np. sprzedano jej akcje) — KEEP, niezależnie od budowy zdania.
4. Fakt musi dotyczyć analizowanej spółki. Konkretna liczba o INNEJ spółce nie ratuje newsa: jeśli o analizowanej spółce nie ma żadnego konkretu, to REJECT.
5. Nie dopasowuj faktu do kategorii. Nie sprawdzaj, czy fakt należy do jakiegoś znanego typu — jakikolwiek konkretny, weryfikowalny fakt o tej spółce wystarczy do KEEP.

Nie grupuj, nie scalaj, nie wybieraj reprezentantów, nie streszczaj, nie komentuj. Każdy numer oceniasz osobno. Kilka newsów o tym samym wydarzeniu to normalne — wszystkie dostają własną etykietę.

Koszt pomyłki nie jest symetryczny: przepuszczenie zbędnego newsa jest tanie, odrzucenie newsa z realnym faktem jest kosztowne. Jeśli się wahasz — KEEP. Nie ma żadnej docelowej proporcji odrzuceń; nie dopasowuj wyniku do żadnego udziału procentowego.

FORMAT ODPOWIEDZI
Jedna linia na KAŻDY numer z wejścia, w kolejności rosnącej, bez żadnego innego tekstu, nagłówków ani komentarzy:
numer|KEEP|kategoria
numer|REJECT|kategoria

Kategoria dla KEEP — wybierz jedną:
RESULTS — wyniki finansowe, prognozy, dane liczbowe spółki
RATING — cena docelowa, rating analityka lub rating kredytowy
DEAL — kontrakt, partnerstwo, zamówienie, inwestycja, przejęcie, finansowanie
POSITION — kupno lub sprzedaż akcji przez inwestora, fundusz albo insidera
REGULATION — decyzja regulacyjna, prawna, sądowa, podatkowa, celna
OPERATIONS — produkt, produkcja, moce wytwórcze, zmiana w zarządzie
OTHER_FACT — inny konkretny, weryfikowalny fakt, nie pasuje do powyższych

Kategoria dla REJECT — wybierz jedną:
NOT_ABOUT_COMPANY — analizowana spółka jest tylko wzmianką na liście albo nie ma jej wcale; treść dotyczy innej firmy
NO_FACT — opinia, komentarz, porównanie, spekulacja, clickbait, ogólny artykuł o wycenie — brak nowego faktu
PRICE_MOVE — wyłącznie o ruchu kursu, sesji albo dziennych zmianach, bez faktu, który je wyjaśnia

KAŻDY numer z wejścia MUSI wystąpić w odpowiedzi dokładnie raz. Nie pomijaj żadnego numeru. Nie wymyślaj numerów, których nie ma na wejściu.

PRZYKŁADY
"Apple Plans to Spend $30 Billion in a Deal With Broadcom (AVGO) – Reuters", streszczenie: generyczny akapit "dlaczego warto kupić akcje Broadcom", bez wzmianki o kwocie → KEEP|DEAL (fakt jest w tytule; niepasujące streszczenie go nie unieważnia)
"What's Going On With Nebius Stock Friday", streszczenie: "Nebius Lands $775 Million AI Funding" → KEEP|DEAL (rutynowy format nagłówka, twardy fakt w streszczeniu)
"Cathie Wood Dumps $39 Million Worth of AMD Stock. SUMMARY: Cathie Wood Trims AMD to Fund Bigger SpaceX Bet", partia dla AMD → KEEP|POSITION (SpaceX jest wyeksponowany, ale sprzedane zostały akcje AMD)
"Micron Technology: Record DRAM Pricing Meets A Stock In Retreat. SUMMARY: Micron just locked in five-year supply deals at historically high DRAM prices... One of them is going to be very wrong." → KEEP|DEAL (narracyjne opakowanie, ale w środku nowa 5-letnia umowa dostawcza)
"Jefferies raises Arm Holdings price target to $320", partia dla Oracle → REJECT|NOT_ABOUT_COMPANY (konkretna liczba, ale o innej spółce; o Oracle nic)
"Meta Vs. Palantir: Meta Platforms' Deep Value Moats Crush Palantir's Hyper-Inflated Multiple" → REJECT|NO_FACT (porównanie wycen, żaden nowy fakt)
"Michael Burry Mocks Data Center 'Fantasy' In ORCL, NVDA, AMZN" → REJECT|NO_FACT (opinia inwestora, żadne działanie nie zostało opisane)
"Burry covers half of his Oracle short bet" → KEEP|POSITION (konkretne działanie inwestycyjne, nawet bez dodatkowych liczb)"""

# FOR THE ENGLISH USERS — English translation of the prompt above.
# The code sends the Polish version. The labels (KEEP/REJECT and the category names) are in English
# in both versions, because they are the output format the rest of the pipeline expects.
#
# You are a financial news filter. You receive a numbered list of news items about ONE company (a [TICKER] label on every line), each as a headline and optionally a summary after "SUMMARY:".
#
# Your only task: for EVERY number in the input, decide KEEP or REJECT.
#
# RULE (the only one):
# Is there a concrete, verifiable fact about the analyzed company in the headline OR in the summary — a number, an amount, a named event, a specific action or decision?
# YES → KEEP. NO → REJECT.
#
# Clarifications of this rule (they are not separate criteria):
# 1. Do not judge by form. The style, format and tone of a headline mean nothing — clickbait, "What's Going On With X Stock", "market movers" roundups, dramatic narrative ("someone is wrong"), promotional tone. That tells you HOW something was written, not WHAT is in it. Always read the summary to the end.
# 2. The headline alone is enough. If the fact is in the headline, it is KEEP — even when the summary is generic, promotional or about something else entirely. In this data summaries are often attached automatically and unrelated to the headline; a mismatched summary does not cancel the fact in the headline.
# 3. The company does not have to be the main subject. It can be mentioned second, at the end of the sentence, next to a bigger or better-known firm. If the fact concerns it (e.g. its shares were sold) — KEEP, regardless of sentence structure.
# 4. The fact must concern the analyzed company. A concrete number about ANOTHER company does not save the news item: if there is nothing concrete about the analyzed company, it is REJECT.
# 5. Do not fit the fact into a category. Do not check whether the fact belongs to some known type — any concrete, verifiable fact about this company is enough for KEEP.
#
# Do not group, merge, pick representatives, summarize or comment. You judge each number separately. Several news items about the same event are normal — each gets its own label.
#
# The cost of a mistake is not symmetric: letting an unnecessary news item through is cheap, rejecting a news item with a real fact is expensive. If in doubt — KEEP. There is no target rejection rate; do not fit the result to any percentage.
#
# RESPONSE FORMAT
# One line for EVERY number in the input, in ascending order, with no other text, headers or comments:
# number|KEEP|category
# number|REJECT|category
#
# Category for KEEP — pick one:
# RESULTS — financial results, guidance, the company's numerical data
# RATING — price target, analyst rating or credit rating
# DEAL — contract, partnership, order, investment, acquisition, financing
# POSITION — purchase or sale of shares by an investor, fund or insider
# REGULATION — regulatory, legal, court, tax or customs decision
# OPERATIONS — product, production, manufacturing capacity, management change
# OTHER_FACT — another concrete, verifiable fact that does not fit the above
#
# Category for REJECT — pick one:
# NOT_ABOUT_COMPANY — the analyzed company is only a mention on a list or is not there at all; the content is about another firm
# NO_FACT — opinion, commentary, comparison, speculation, clickbait, a general valuation article — no new fact
# PRICE_MOVE — only about the share price move, the session or daily changes, with no fact that explains them
#
# EVERY number in the input MUST appear in the response exactly once. Do not skip any number. Do not invent numbers that are not in the input.
#
# EXAMPLES
# "Apple Plans to Spend $30 Billion in a Deal With Broadcom (AVGO) – Reuters", summary: a generic paragraph "why Broadcom stock is worth buying", no mention of the amount → KEEP|DEAL (the fact is in the headline; a mismatched summary does not cancel it)
# "What's Going On With Nebius Stock Friday", summary: "Nebius Lands $775 Million AI Funding" → KEEP|DEAL (routine headline format, hard fact in the summary)
# "Cathie Wood Dumps $39 Million Worth of AMD Stock. SUMMARY: Cathie Wood Trims AMD to Fund Bigger SpaceX Bet", batch for AMD → KEEP|POSITION (SpaceX is emphasized, but it was AMD shares that were sold)
# "Micron Technology: Record DRAM Pricing Meets A Stock In Retreat. SUMMARY: Micron just locked in five-year supply deals at historically high DRAM prices... One of them is going to be very wrong." → KEEP|DEAL (narrative wrapping, but inside there is a new 5-year supply deal)
# "Jefferies raises Arm Holdings price target to $320", batch for Oracle → REJECT|NOT_ABOUT_COMPANY (a concrete number, but about another company; nothing about Oracle)
# "Meta Vs. Palantir: Meta Platforms' Deep Value Moats Crush Palantir's Hyper-Inflated Multiple" → REJECT|NO_FACT (a valuation comparison, no new fact)
# "Michael Burry Mocks Data Center 'Fantasy' In ORCL, NVDA, AMZN" → REJECT|NO_FACT (an investor's opinion, no action is described)
# "Burry covers half of his Oracle short bet" → KEEP|POSITION (a concrete investment action, even without additional numbers)


STAGE1_SYSTEM_PROMPT_OLD = """Jesteś pierwszym filtrem w systemie analizy newsów finansowych. Dostajesz ponumerowaną listę tytułów i krótkich streszczeń newsów z ostatniego tygodnia, każdy z etykietą [TICKER].

KROK 1 - ODSIEWANIE (najważniejsze zadanie):
Odrzuć CAŁKOWICIE (nie wypisuj ich wcale w odpowiedzi) tytuły, które są:
- czystym clickbaitem bez konkretnej treści,
- listami rynkowymi / podsumowaniami sesji ("najbardziej aktywne akcje S&P500", "co się dzieje w dzisiejszej sesji"),
- ogólnymi artykułami rynkowymi, w których spółka jest wspomniana tylko mimochodem (jedna z wielu nazw na liście),
- artykułami, które W OGÓLE nie dotyczą analizowanej spółki (spółka nie jest wspomniana ani w tytule, ani w streszczeniu — cała treść dotyczy innej firmy lub wydarzenia, np. błędnie otagowany news). To odrzucenie ma PIERWSZEŃSTWO przed wszystkimi innymi kryteriami, łącznie z wyjątkiem dla konkretnej liczby poniżej — konkretna liczba dotycząca INNEJ spółki nie ratuje artykułu. UWAGA: jeśli tytuł wymienia WIĘCEJ NIŻ JEDNĄ spółkę (np. "...to Fund Bigger X Bet", "— Trims Y and Z"), NIE odrzucaj automatycznie tylko dlatego, że analizowana spółka jest gramatycznie drugorzędna/końcowa w zdaniu, a inna spółka jest wymieniona jako pierwsza lub bardziej wyeksponowana — sprawdź, czy artykuł opisuje konkretne działanie lub fakt DOTYCZĄCY analizowanej spółki (np. sprzedano/kupiono jej akcje); jeśli tak, ZACHOWAJ niezależnie od struktury zdania,
- drobnymi ogłoszeniami partnerskimi/produktowymi bez istotnego wpływu na wyniki lub pozycję konkurencyjną spółki,
- ogólnymi artykułami opinii/analizy o spółce (porównania "co lepiej kupić", rozważania o wycenie, komentarze bez nowej informacji) — ODRZUĆ je, JEŚLI nie zawierają konkretnego nowego FAKTU DOTYCZĄCEGO ANALIZOWANEJ SPÓŁKI. Jeśli zawierają taki fakt i dotyczą tej spółki, NIE odrzucaj — to przechodzi normalnie do grupowania.

Co liczy się jako "konkretny nowy fakt" (lista PRZYKŁADOWA, NIE wyczerpująca — traktuj ją jako wzorzec, nie zamkniętą listę kategorii):
nowa cena docelowa, zmiana ratingu domu maklerskiego, wynik finansowy, zmiana ratingu kredytowego, konkretne zobowiązanie finansowe/prawne (kwota, kara, zabezpieczenie), znacząca zmiana pozycji inwestycyjnej rozpoznawalnego inwestora/funduszu, decyzja regulacyjna lub prawna, konkretny kontrakt/umowa. Jeśli artykuł podaje jakąkolwiek konkretną, weryfikowalną liczbę lub zdarzenie dotyczące analizowanej spółki (niezależnie czy pasuje do jednej z powyższych kategorii) — ZACHOWAJ go. Odrzucaj na podstawie tej reguły wyłącznie czysty komentarz/opinię BEZ żadnego nowego faktu, nie na podstawie tego, czy fakt pasuje do konkretnej znanej Ci kategorii.

Newsy o konkretnych inwestorach/funduszach: odróżnij OPINIĘ (co inwestor sądzi, prognozuje, komentuje, czego jest sceptyczny — to NIE jest fakt, ODRZUĆ) od KONKRETNEGO DZIAŁANIA (co inwestor faktycznie zrobił: kupił, sprzedał, zamknął lub zmniejszył/zwiększył pozycję — to ZAWSZE jest fakt, ZACHOWAJ). Jeśli tytuł opisuje konkretne działanie, ZACHOWAJ go, nawet jeśli streszczenie nie dokłada żadnej dodatkowej liczby uzasadniającej kontekst (np. samego poziomu ceny akcji) — sam fakt zmiany pozycji wystarczy, nie wymagaj potwierdzenia drugą liczbą.

Jeśli TYTUŁ zawiera konkretny, weryfikowalny fakt (liczbę, kwotę, nazwane wydarzenie), zwłaszcza z przypisaniem do źródła (np. "– Reuters", "– Bloomberg"), ZACHOWAJ artykuł nawet jeśli STRESZCZENIE jest generyczne, promocyjne albo w ogóle nie odnosi się do tego faktu z tytułu. To częsty przypadek w danych: automatycznie wygenerowane streszczenie z niepasującej, ogólnej treści (np. akapit "dlaczego kupić akcje X") doklejone do konkretnego, twardego newsa. Nie wymagaj, żeby streszczenie potwierdzało fakt z tytułu — sam tytuł z konkretną liczbą i źródłem wystarczy, streszczenie nie może "unieważnić" faktu z tytułu samą swoją ogólnikowością.

WAŻNE OGÓLNE OSTRZEŻENIE: nie oceniaj artykułu na podstawie STYLU, FORMATU czy GATUNKU nagłówka (np. "Why Is X Stock Up/Down Today", "What's Going On With X Stock", zestawienia typu "market movers" z wieloma tickerami naraz, ton promocyjny lub clickbaitowy, DRAMATYCZNE/NARRACYJNE sformułowania typu "ktoś się myli", "jedno z nich okaże się błędem", kontrastowe zestawienie dwóch stron sporu) — to sygnały o tym JAK coś jest napisane, nie o tym CO jest w treści. Nagłówek, który ma format zwykle kojarzony z szumem ALBO brzmi jak dramatyczna narracja/spekulacja, może mimo to kryć w streszczeniu konkretny, ważny fakt (np. nową umowę, kontrakt, liczbę) — zawsze czytaj streszczenie do końca, niezależnie od tego, jak nieistotnie, rutynowo czy narracyjnie wygląda sam tytuł. Działa to też w drugą stronę: poważnie brzmiący, rozbudowany nagłówek bez żadnego faktu w streszczeniu nadal ODRZUĆ.

PRZYKŁADY GRANICZNE:
- ODRZUĆ: "Palantir's Wild Ride: Inside the Stock Wall Street Can't Agree On" — ogólna narracja o niezgodzie rynku, brak konkretnej nowej liczby czy wydarzenia.
- ODRZUĆ: "Meta Vs. Palantir: Meta Platforms' Deep Value Moats Crush Palantir's Hyper-Inflated Multiple" — subiektywne porównanie wycen, brak konkretnej nowej informacji.
- ODRZUĆ MIMO LICZBY: "Jefferies raises Arm Holdings price target to $320" w partii dla Oracle — konkretna liczba, ale dotyczy zupełnie innej spółki (Arm); Oracle nie jest nawet wspomniane.
- ZACHOWAJ: "CLSA Starts Oracle With Hold on AI Debt Concerns" — konkretny nowy rating ("Hold") od konkretnego domu maklerskiego, DLA analizowanej spółki (Oracle).
- ZACHOWAJ: "Jefferies Raises Oracle Price Target to $350 on Cloud Growth" — konkretna nowa cena docelowa DLA analizowanej spółki.
- ZACHOWAJ: "Oracle could face $7bn collateral bill for Wisconsin data centre" — konkretne zobowiązanie finansowe (kwota), nawet jeśli to nie cena docelowa ani rating.
- ZACHOWAJ: "Oracle Just Hit a Fresh 52-Week Low and Had Its Credit Cut Toward Junk" — konkretna zmiana ratingu kredytowego, realne wydarzenie.
- ODRZUĆ: "Michael Burry Mocks Data Center 'Fantasy' In ORCL, NVDA, AMZN — But Trump Sees 'Big, Strong, Bold' Money Machines" — OPINIA/komentarz inwestora o rynku, brak jakiegokolwiek opisanego DZIAŁANIA (nic nie kupił, nie sprzedał, nie zmienił).
- ZACHOWAJ: "Burry covers half of his Oracle short bet" — konkretne DZIAŁANIE inwestycyjne (zamknięcie połowy pozycji) rozpoznawalnego inwestora; ZACHOWAJ mimo że streszczenie skupia się na poziomie ceny akcji, a nie na szczegółach samej transakcji.
- ZACHOWAJ MIMO NIEPASUJĄCEGO STRESZCZENIA: "Apple Plans to Spend $30 Billion in a Deal With Broadcom (AVGO) – Reuters" — konkretna liczba i przypisanie do źródła (Reuters) w samym tytule, mimo że streszczenie to niepowiązany, generyczny akapit typu "dlaczego kupić akcje Broadcom" bez żadnej wzmianki o kwocie $30 mld.
- ZACHOWAJ MIMO RUTYNOWEGO FORMATU NAGŁÓWKA: "What's Going On With Nebius Stock Friday" — nagłówek ma format typowego, rutynowego pytania o dzienny ruch ceny (ten format zwykle = szum), ale streszczenie zawiera konkretny fakt: "Nebius Lands $775 Million AI Funding" — sam format nagłówka nie przesądza, liczy się treść streszczenia.
- ZACHOWAJ MIMO DRUGORZĘDNEGO WSPOMNIENIA: "Cathie Wood Dumps $39 Million Worth of AMD Stock. SUMMARY: Cathie Wood Trims AMD to Fund Bigger SpaceX Bet" (partia dla AMD) — SpaceX jest wymieniony jako cel przekierowania środków i jest gramatycznie wyeksponowany na końcu zdania, ale to AMD jest realnym obiektem sprzedanej pozycji — konkretne działanie inwestycyjne dotyczące analizowanej spółki, ZACHOWAJ niezależnie od tego, która nazwa spółki "brzmi" ważniej w zdaniu.
- ZACHOWAJ MIMO DRAMATYCZNEJ/NARRACYJNEJ FORMY NAGŁÓWKA: "Micron Technology: Record DRAM Pricing Meets A Stock In Retreat. SUMMARY: Micron just locked in five-year supply deals at historically high DRAM prices while a major AI cloud buyer quietly bets those same prices are about to fall. One of them is going to be very wrong." — nagłówek i część streszczenia brzmią jak spekulacyjna narracja ("ktoś się myli"), ale zawiera konkretny fakt: nowa 5-letnia umowa dostawcza przy rekordowych cenach DRAM — ZACHOWAJ ze względu na ten fakt, niezależnie od narracyjnego opakowania.

To odsiewanie jest kluczowe: w typowej partii newsów WIĘKSZOŚĆ (często 60-80%) powinna zostać odrzucona. Lepiej odrzucić zbyt wiele niż zbyt mało.

KROK 2 - GRUPOWANIE:
Z tego, co PRZESZŁO odsiewanie, pogrupuj tytuły opisujące to samo wydarzenie w jedną historię.

KROK 3 - WYBÓR REPREZENTANTA(-ÓW):
Dla każdej pozostałej historii wybierz JEDEN numer reprezentatywny (najbardziej konkretny/informacyjny tytuł z grupy). WYJĄTEK: jeśli w grupie żaden pojedynczy artykuł nie zawiera wszystkich kluczowych, różniących się faktów (np. jeden podaje procent/skalę wydarzenia, inny podaje konkretną kwotę w dolarach lub inny szczegół, którego pierwszy nie ma) — wybierz DWA numery reprezentatywne, które razem pokrywają te różne fakty. Nie wybieraj więcej niż dwóch nawet jeśli grupa jest duża.

Przykład: klaster kilku newsów o tym, że NVIDIA zgłosiła 9,3% udziału w spółce X — jeden artykuł podaje "9,3% udziału, akcje +18%", inny podaje "prawie $4 mld, zwiększenie udziału 18-krotnie" — żaden pojedynczy artykuł nie ma obu tych liczb. Wybierz oba te numery jako reprezentantów, nie tylko jeden.

Odpowiedz WYŁĄCZNIE w formacie, jedna historia na linię, bez żadnego innego tekstu, nagłówków czy komentarzy:
numer_reprezentanta|numer1,numer2,numer3
lub, gdy grupa potrzebuje dwóch reprezentantów (patrz WYJĄTEK wyżej):
numer_reprezentanta1,numer_reprezentanta2|numer1,numer2,numer3

Gdzie: numer(y) reprezentanta (jeden lub dwa, oddzielone przecinkiem bez spacji, przed |) to numer(y) wybranego tytułu/tytułów, a lista po | to WSZYSTKIE numery tytułów należące do tej historii (włącznie z reprezentantem/reprezentantami), oddzielone przecinkami bez spacji. KAŻDY numer może wystąpić w CAŁEJ odpowiedzi TYLKO RAZ — jeśli numer już przypisałeś do jednej historii, nie umieszczaj go w żadnej innej linii.

Nie sortuj linii — kolejność nie ma znaczenia. Tylko linie w podanym formacie, wyłącznie dla historii, które przeszły odsiewanie."""



companies = {
    #"PLTR": {"name": "Palantir Technologies", "related": [], "role": "portfolio"},
    "AVGO": {"name": "Broadcom", "related": [], "role": "portfolio"},
    #"NVDA": {"name": "NVIDIA Corporation", "related": [], "role": "portfolio"},
    "AMD": {"name": "Advanced Micro Devices", "related": [], "role": "portfolio"},

    #"ORCL": {"name": "Oracle", "related": [], "role":"watchlist"},
    "SNOW": {"name": "Snowflake", "related": [], "role":"competitor"},
    #"000660.KS": {"name": "SK Hynix", "related": [], "role": "watchlist"}, # 403 on Finnhub - no access to the Korean exchange on this plan
    "MU": {"name": "Micron Technology", "related": [], "role": "watchlist"},
    #"NBIS": {"name": "Nebius Group", "related": [], "role": "watchlist"},
    "CRDO": {"name": "Credo Technology", "related": [], "role": "watchlist"},
    #"CEG": {"name": "Constellation Energy", "related": [], "role": "watchlist"},
    #"GEV": {"name": "GE Vernova", "related": [], "role": "watchlist"},
    #"APP": {"name": "AppLovin", "related": [], "role": "watchlist"}
    # "MSFT": {"name": "Microsoft"}
}

if SOURCE == "api":
    def fetch_news(ticker):
        today = datetime.now(timezone.utc)
        week_ago = today - timedelta(days=7)

        today = today.strftime("%Y-%m-%d")
        week_ago = week_ago.strftime("%Y-%m-%d")

        #query_params = {"symbol": ticker, "from": week_ago, "to": today, "token": FINNHUB_KEY}
        query_params = {"symbol": ticker, "from":"2026-07-15" , "to":"2026-07-22", "token": FINNHUB_KEY}

        response = requests.get("https://finnhub.io/api/v1/company-news", params=query_params)
        return response.json()
    

    all_news = []
    tickers = list(companies.keys())
    print(tickers)
    for ticker, info in companies.items():

        news_items = fetch_news(ticker)
        for single_news in news_items:
            single_news["ticker"] = ticker
        #pprint.pprint(news_items)
        all_news.extend(news_items)

    with open("data/news_2026-07-15_2026-07-22.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(len(all_news))
    
else:
    with open("data/news_2026-07-15_2026-07-22.json", "r", encoding="utf-8") as f:
        all_news = json.load(f)
    
    
print(len(all_news))

#DUPLICATES 

unique_news = []

seen_pairs = set()
#seen_ticker = set()

#pprint.pprint(all_news)

for news in all_news:
    news_id = news["id"] # bug was here: only SNOW got fetched - found why: there was only news_items and I was not adding it to the list (all_news)
    news_ticker = news["ticker"]
    pair = (news_id, news_ticker)
    #news_ticker = news["ticker"]
    if pair not in seen_pairs:
        seen_pairs.add(pair)
        #seen_ticker.add(news_ticker)

        unique_news.append(news)

print(len(unique_news))
#pprint.pprint(unique_news)

#pprint.pprint(unique_news[0])

#---------

def classify_news(news_list):
    headlines = []
    responses = []

    lines_by_ticker = {}

    for number, news in enumerate(news_list, start = 1):
        if news["summary"] == "":
            #headlines.append(f"{number}. [{news["ticker"]}] {news["headline"]}")
            lines_by_ticker.setdefault(news["ticker"], []).append(f"{number}. [{news["ticker"]}] {news["headline"]}")
        else:
            #headlines.append(f"{number}. [{news["ticker"]}] {news["headline"]}. SUMMARY: {news["summary"]}")
            lines_by_ticker.setdefault(news["ticker"], []).append(f"{number}. [{news["ticker"]}] {news["headline"]}. SUMMARY: {news["summary"]}")
        
    #print(lines_by_ticker)
    
    with open("data/headlines_by_ticker_2026-07-15_2026-07-22.json", "w", encoding="utf-8") as f:
        json.dump(lines_by_ticker, f, ensure_ascii=False, indent=2)
    
    #clear the responses file on every new run
    with open("data/responses_2026-07-15_2026-07-22.jsonl", "w", encoding="utf-8") as f:
        pass


    for ticker, lines in lines_by_ticker.items():

        for offset in range(0,len(lines),100):
            batch_text = "\n".join(lines[offset:offset+100])
            print(batch_text)

            # To test for free (without the real API): comment out the call
            # API_CLAUDE.messages.create(...) below and put this instead:
            #response = fake_call(model="claude-haiku-4-5", max_tokens=3500, temperature=0, system=STAGE1_SYSTEM_PROMPT, messages=[{"role": "user", "content": batch_text}])
            # (fake_call and FakeResponse are defined at the top of the file, next to API_CLAUDE = Anthropic())

            response = API_CLAUDE.messages.create(
            model="claude-haiku-4-5",
            max_tokens=3500,
            temperature=0,
            system=STAGE1_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": batch_text}])

            responses.append(response.content[0].text)

            print("+++++++++++++++++++++++++++++++")
            print(response.content[0].text)
            print("------------------------------------")

            response_record = {
                "ticker":ticker,
                "offset":offset,
                "input":batch_text,
                "response":response.content[0].text
            }

            with open("data/responses_2026-07-15_2026-07-22.jsonl", "a", encoding="utf-8") as f:
                json.dump(response_record, f, ensure_ascii=False)
                f.write("\n")

            # with open("data/archive/responses_v13_2026-07-15_2026-07-22.jsonl", encoding="utf-8") as f:
            #     for line in f:
            #         entry = json.loads(line)
            #         pprint.pprint(entry)
                



    return("\n".join(responses))


    # for ticker, batch_text in final_text_by_ticker:
    #     print(f"=== {ticker} ===")
    #     print(batch_text)


classify_news(unique_news) # or unique_news

