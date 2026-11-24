"""Plain-language explainers for US industries: what such a company does, how it makes money, and which parts of
the economy move it. Keyed by GICS sub-industry first, then by GICS sector.

Factors are raw directions of a number the page can watch:
  oil     crude oil price            (+1 = the business gains when crude rises)
  rates   10-year Treasury yield     (+1 = gains when yields rise, -1 = hurt by higher yields)
  usd     the dollar index           (+1 = gains when the dollar strengthens, -1 = hurt: foreign sales shrink in dollars)
  metals  copper                     (+1 = gains when metal prices rise, -1 = input cost)
  us      the S&P 500 itself         (+1 = does well when the stock market and the economy do)
  reg     regulation and approvals   (no reading: shown as a risk or tailwind, never measured)
  china   cheap imports / China      (no reading)
"""

FACTOR_NAMES = {"oil": "Crude oil price", "rates": "Treasury yields (interest rates)", "usd": "The US dollar", "metals": "Copper and metal prices",
                "us": "The US stock market and economy", "reg": "Regulation and approvals", "china": "China and cheap imports"}

IND = {
    "Semiconductors": ("Designs or makes computer chips: processors, memory, graphics and chips for cars and phones.",
                       [("us", 1, "chip demand follows tech spending and the AI build-out"), ("china", -1, "export limits and local rivals"), ("usd", -1, "most sales are abroad")]),
    "Semiconductor Materials & Equipment": ("Builds the machines and materials chipmakers use to make chips.", [("us", 1, "chip factories' spending plans"), ("china", -1, "export limits on China sales")]),
    "Application Software": ("Sells software people and companies use for work: subscriptions, tools and apps.", [("rates", -1, "growth software is valued on distant profits, so higher yields hurt"), ("us", 1, "company tech budgets")]),
    "Systems Software": ("Sells the underlying software of computers and networks: operating systems, cloud tools, security.", [("us", 1, "company tech budgets"), ("rates", -1, "higher yields cut valuations")]),
    "Technology Hardware, Storage & Peripherals": ("Makes phones, computers, servers and storage and sells them to people and companies.", [("us", 1, "consumer and company upgrade cycles"), ("usd", -1, "a large share of sales is abroad"), ("china", -1, "supply chain and sales exposure")]),
    "Interactive Media & Services": ("Earns mostly from advertising on search, social and video platforms.", [("us", 1, "advertisers spend more when the economy is strong"), ("reg", -1, "antitrust and privacy rules")]),
    "Broadline Retail": ("Sells a wide range of goods online or in big stores.", [("us", 1, "consumer spending"), ("rates", -1, "borrowing costs for shoppers")]),
    "Automobile Manufacturers": ("Builds and sells cars and trucks.", [("rates", -1, "car loans get dearer when yields rise"), ("metals", -1, "steel and aluminium costs"), ("china", -1, "Chinese rivals and tariffs")]),
    "Diversified Banks": ("Takes deposits and lends them out; also runs cards, investment banking and wealth management.", [("rates", 1, "wider gap between loan and deposit rates"), ("us", 1, "loan demand and credit quality"), ("reg", -1, "capital rules")]),
    "Regional Banks": ("Local and regional banks: deposits in, loans out, mostly in one part of the country.", [("rates", 0, "higher yields help loan income but hurt bond holdings and deposits"), ("us", 1, "local business health"), ("reg", -1, "capital rules after 2023")]),
    "Investment Banking & Brokerage": ("Helps companies raise money and merge, and trades for clients; earns fees and trading profit.", [("us", 1, "deal and trading activity follow markets"), ("rates", -1, "high yields slow deals")]),
    "Asset Management & Custody Banks": ("Manages other people's money and charges a fee on the amount.", [("us", 1, "fees rise when markets rise"), ("rates", -1, "yields compete with stocks")]),
    "Property & Casualty Insurance": ("Sells car, home and business insurance; earns the premium minus claims, plus returns on what it holds.", [("rates", 1, "higher yields lift investment income"), ("reg", 0, "state price approvals")]),
    "Life & Health Insurance": ("Sells life insurance and annuities and invests the money.", [("rates", 1, "higher yields lift investment income")]),
    "Biotechnology": ("Develops new drugs; most have no sales until a drug is approved.", [("reg", 0, "FDA decisions make or break a drug"), ("rates", -1, "unprofitable firms depend on cheap funding")]),
    "Pharmaceuticals": ("Makes and sells prescription drugs.", [("reg", -1, "drug price rules and patent expiry"), ("usd", -1, "large foreign sales")]),
    "Health Care Equipment": ("Makes medical devices: implants, monitors, surgical tools.", [("us", 1, "hospital spending and procedure volumes"), ("reg", 0, "device approvals")]),
    "Managed Health Care": ("Sells health insurance and runs the plans.", [("reg", -1, "Medicare and Medicaid payment rules"), ("us", 0, "medical costs vs premiums")]),
    "Life Sciences Tools & Services": ("Sells instruments and services to labs and drug companies.", [("us", 1, "research budgets"), ("rates", -1, "biotech funding")]),
    "Integrated Oil & Gas": ("Finds, produces, refines and sells oil and gas.", [("oil", 1, "revenue follows crude and gas prices"), ("usd", -1, "oil is priced in dollars")]),
    "Oil & Gas Exploration & Production": ("Finds and pumps oil and gas and sells it at market prices.", [("oil", 1, "revenue follows crude and gas prices")]),
    "Oil & Gas Equipment & Services": ("Sells drilling and field services to oil producers.", [("oil", 1, "producers spend more when crude is high")]),
    "Oil & Gas Refining & Marketing": ("Refines crude into fuel; earns the gap between crude cost and fuel prices.", [("oil", 0, "margins depend on the gap, not the level")]),
    "Passenger Airlines": ("Flies people; earns ticket sales minus fuel, crews and planes.", [("oil", -1, "jet fuel is a top cost"), ("us", 1, "travel demand"), ("rates", -1, "planes are financed with debt")]),
    "Homebuilding": ("Builds and sells homes.", [("rates", -1, "mortgage rates decide who can buy"), ("us", 1, "buyer confidence")]),
    "Aerospace & Defense": ("Builds aircraft, engines, missiles, ships and electronics for airlines and governments.", [("reg", 0, "government budgets and contracts"), ("us", 1, "air travel recovery")]),
    "Industrial Machinery & Supplies & Components": ("Makes machines and parts used in factories and construction.", [("us", 1, "factory and construction spending"), ("metals", -1, "steel and copper costs")]),
    "Construction & Engineering": ("Builds infrastructure, plants and buildings for governments and companies.", [("us", 1, "project spending"), ("rates", -1, "projects run on borrowed money")]),
    "Rail Transportation": ("Hauls freight on railroads.", [("us", 1, "factory and shipping volumes"), ("oil", -1, "diesel cost")]),
    "Electric Utilities": ("Generates and delivers electricity at prices set by regulators.", [("rates", -1, "heavy debt and bond-like shares fall when yields rise"), ("reg", 0, "regulators set allowed returns")]),
    "Multi-Utilities": ("Delivers electricity and gas under regulated rates.", [("rates", -1, "bond-like shares fall when yields rise"), ("reg", 0, "regulated returns")]),
    "Renewable Electricity": ("Runs solar, wind and other clean power plants.", [("rates", -1, "projects are built with debt"), ("reg", 1, "tax credits and subsidies")]),
    "Gold": ("Mines gold.", [("usd", -1, "gold tends to rise when the dollar falls"), ("rates", -1, "high real yields hurt gold")]),
    "Steel": ("Makes steel for cars, buildings and machinery.", [("metals", 1, "steel prices"), ("china", -1, "cheap imports")]),
    "Copper": ("Mines copper.", [("metals", 1, "copper price"), ("china", 1, "China buys much of the world's copper")]),
    "Specialty Chemicals": ("Makes special chemicals for paints, electronics, farming and more.", [("us", 1, "factory activity"), ("oil", -1, "raw material costs"), ("china", -1, "cheap imports")]),
    "Packaged Foods & Meats": ("Makes packaged food sold in grocery stores.", [("us", 0, "steady demand, input costs matter"), ("oil", -1, "transport and packaging")]),
    "Soft Drinks & Non-alcoholic Beverages": ("Makes and sells drinks.", [("usd", -1, "large foreign sales"), ("us", 0, "steady demand")]),
    "Restaurants": ("Runs restaurants and franchises.", [("us", 1, "people eat out more when jobs are good"), ("rates", -1, "borrowing and consumer budgets")]),
    "Hotels, Resorts & Cruise Lines": ("Runs hotels, resorts and cruise ships.", [("us", 1, "travel demand"), ("oil", -1, "fuel for cruise lines")]),
    "Data Center REITs": ("Owns the buildings and power that house computer servers.", [("us", 1, "cloud and AI demand"), ("rates", -1, "REITs borrow heavily")]),
    "Office REITs": ("Owns and rents office buildings.", [("rates", -1, "borrowing costs"), ("us", 1, "office demand")]),
    "Specialized Finance": ("Provides specialised financial services such as exchanges and payment networks.", [("us", 1, "trading and payment volumes")]),
    "Transaction & Payment Processing Services": ("Moves payments between shoppers, shops and banks and takes a small fee on each.", [("us", 1, "consumer spending"), ("usd", -1, "cross-border volumes")]),
}

SECTOR_DEFAULT = {
    "Information Technology": ("Technology company.", [("us", 1, "company and consumer tech spending"), ("rates", -1, "growth shares fall when yields rise")]),
    "Communication Services": ("Media, telecom or internet platform company.", [("us", 1, "advertising and subscriptions")]),
    "Consumer Discretionary": ("Sells things people buy when they have spare money.", [("us", 1, "consumer spending"), ("rates", -1, "loans cost more")]),
    "Consumer Staples": ("Sells everyday essentials: food, drink, household goods.", [("us", 0, "steady demand"), ("oil", -1, "transport and packaging costs")]),
    "Health Care": ("Healthcare company.", [("reg", 0, "approvals and payment rules")]),
    "Financials": ("Financial company: earns from lending, fees, insurance or investing.", [("rates", 0, "yields move margins both ways"), ("us", 1, "economic activity")]),
    "Industrials": ("Makes industrial goods or builds projects.", [("us", 1, "factory and project spending")]),
    "Energy": ("Energy company.", [("oil", 1, "energy prices")]),
    "Materials": ("Makes basic materials.", [("metals", 1, "commodity prices"), ("china", -1, "China demand and cheap exports")]),
    "Real Estate": ("Owns property or earns from it.", [("rates", -1, "borrowing costs and bond-like shares")]),
    "Utilities": ("Supplies power, gas or water at regulated prices.", [("rates", -1, "bond-like shares"), ("reg", 0, "regulated returns")]),
}

MARGIN_NORM = {"Information Technology": 18, "Communication Services": 12, "Consumer Discretionary": 7, "Consumer Staples": 8, "Health Care": 10,
               "Financials": 18, "Industrials": 9, "Energy": 8, "Materials": 8, "Real Estate": 15, "Utilities": 11, "Other": 8}


def lookup(sub, sector):
    return IND.get(sub) or SECTOR_DEFAULT.get(sector) or ("Listed company.", [])
