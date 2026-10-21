#!/usr/bin/env python3
"""Seed the database with European companies hiring DevOps/Platform/SRE talent."""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import sync_engine, SessionLocal
from app.models.company import Company
from app.models.country import Country

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parents[2]
SEED_FILE = BASE_DIR / "seed-data" / "companies.json"

# Well-known companies across target countries that hire DevOps/Platform/SRE.
KNOWN_COMPANIES = [
    # UK
    {"name": "ARM", "country": "GB", "city": "Cambridge", "industry": "Semiconductors", "size": "5000+", "career_page_url": "https://careers.arm.com/", "ats_provider": "Workday"},
    {"name": "BAE Systems", "country": "GB", "city": "London", "industry": "Defense", "size": "5000+", "career_page_url": "https://www.baesystems.com/en/careers/", "ats_provider": "Taleo"},
    {"name": "BBC", "country": "GB", "city": "London", "industry": "Media", "size": "5000+", "career_page_url": "https://www.bbc.co.uk/careers/", "ats_provider": "Workday"},
    {"name": "Booking.com", "country": "GB", "city": "London", "industry": "Travel", "size": "5000+", "career_page_url": "https://jobs.booking.com/", "ats_provider": "Workday"},
    {"name": "Bristol Myers Squibb", "country": "GB", "city": "Uxbridge", "industry": "Pharma", "size": "5000+", "career_page_url": "https://careers.bms.com/", "ats_provider": "Workday"},
    {"name": "BT Group", "country": "GB", "city": "London", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.bt.com/careers", "ats_provider": "Workday"},
    {"name": "Checkout.com", "country": "GB", "city": "London", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.checkout.com/careers#jobs", "ats_provider": "Greenhouse"},
    {"name": "Deliveroo", "country": "GB", "city": "London", "industry": "Food Delivery", "size": "1001-5000", "career_page_url": "https://careers.deliveroo.co.uk/", "ats_provider": "Greenhouse"},
    {"name": "Dyson", "country": "GB", "city": "Malmesbury", "industry": "Consumer Electronics", "size": "5000+", "career_page_url": "https://www.dysoncareers.com/", "ats_provider": "Workday"},
    {"name": "Farfetch", "country": "GB", "city": "London", "industry": "E-commerce", "size": "1001-5000", "career_page_url": "https://aboutfarfetch.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Goldman Sachs", "country": "GB", "city": "London", "industry": "Finance", "size": "5000+", "career_page_url": "https://www.goldmansachs.com/careers/", "ats_provider": "Workday"},
    {"name": "Google UK", "country": "GB", "city": "London", "industry": "Tech", "size": "5000+", "career_page_url": "https://careers.google.com/", "ats_provider": "Internal"},
    {"name": "HSBC", "country": "GB", "city": "London", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.hsbc.com/careers", "ats_provider": "Workday"},
    {"name": "Improbable", "country": "GB", "city": "London", "industry": "Gaming", "size": "201-1000", "career_page_url": "https://jobs.improbable.io/", "ats_provider": "Greenhouse"},
    {"name": "JPMorgan Chase", "country": "GB", "city": "London", "industry": "Finance", "size": "5000+", "career_page_url": "https://jpmc.fa.oraclecloud.com/", "ats_provider": "Oracle"},
    {"name": "Monzo", "country": "GB", "city": "London", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://monzo.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "NatWest", "country": "GB", "city": "London", "industry": "Banking", "size": "5000+", "career_page_url": "https://jobs.natwestgroup.com/", "ats_provider": "Workday"},
    {"name": "Revolut", "country": "GB", "city": "London", "industry": "Fintech", "size": "5000+", "career_page_url": "https://www.revolut.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Sainsbury's", "country": "GB", "city": "London", "industry": "Retail", "size": "5000+", "career_page_url": "https://sainsburys.jobs/", "ats_provider": "Taleo"},
    {"name": "Sky", "country": "GB", "city": "London", "industry": "Media", "size": "5000+", "career_page_url": "https://www.skygroupcareers.com/", "ats_provider": "Workday"},
    {"name": "Spotify", "country": "GB", "city": "London", "industry": "Music", "size": "5000+", "career_page_url": "https://www.lifeatspotify.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Starling Bank", "country": "GB", "city": "London", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://www.starlingbank.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Thought Machine", "country": "GB", "city": "London", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://www.thoughtmachine.net/careers", "ats_provider": "Greenhouse"},
    {"name": "Wise", "country": "GB", "city": "London", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.wise.jobs/", "ats_provider": "Greenhouse"},
    # Ireland
    {"name": "Accenture", "country": "IE", "city": "Dublin", "industry": "Consulting", "size": "5000+", "career_page_url": "https://www.accenture.com/ie-en/careers", "ats_provider": "Workday"},
    {"name": "AIB", "country": "IE", "city": "Dublin", "industry": "Banking", "size": "5000+", "career_page_url": "https://aib.ie/careers", "ats_provider": "Workday"},
    {"name": "Bank of Ireland", "country": "IE", "city": "Dublin", "industry": "Banking", "size": "5000+", "career_page_url": "https://bankofireland.com/careers/", "ats_provider": "Workday"},
    {"name": "Circle", "country": "IE", "city": "Dublin", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://www.circle.com/en/careers", "ats_provider": "Greenhouse"},
    {"name": "Citi", "country": "IE", "city": "Dublin", "industry": "Finance", "size": "5000+", "career_page_url": "https://jobs.citi.com/", "ats_provider": "Taleo"},
    {"name": "Google Ireland", "country": "IE", "city": "Dublin", "industry": "Tech", "size": "5000+", "career_page_url": "https://careers.google.com/locations/dublin/", "ats_provider": "Internal"},
    {"name": "HubSpot", "country": "IE", "city": "Dublin", "industry": "SaaS", "size": "1001-5000", "career_page_url": "https://www.hubspot.com/careers", "ats_provider": "Greenhouse"},
    {"name": "Indeed Ireland", "country": "IE", "city": "Dublin", "industry": "Job Board", "size": "5000+", "career_page_url": "https://www.indeed.com/careers", "ats_provider": "Internal"},
    {"name": "Meta", "country": "IE", "city": "Dublin", "industry": "Tech", "size": "5000+", "career_page_url": "https://www.metacareers.com/", "ats_provider": "Workday"},
    {"name": "Microsoft Ireland", "country": "IE", "city": "Dublin", "industry": "Tech", "size": "5000+", "career_page_url": "https://careers.microsoft.com/", "ats_provider": "Internal"},
    {"name": "Ryanair", "country": "IE", "city": "Dublin", "industry": "Aviation", "size": "5000+", "career_page_url": "https://careers.ryanair.com/", "ats_provider": "Workday"},
    {"name": "Shopify", "country": "IE", "city": "Dublin", "industry": "E-commerce", "size": "5000+", "career_page_url": "https://www.shopify.com/careers", "ats_provider": "Greenhouse"},
    {"name": "Stripe", "country": "IE", "city": "Dublin", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://stripe.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Workday", "country": "IE", "city": "Dublin", "industry": "SaaS", "size": "5000+", "career_page_url": "https://www.workday.com/en-us/company/careers.html", "ats_provider": "Internal"},
    # Germany
    {"name": "Airbus", "country": "DE", "city": "Munich", "industry": "Aerospace", "size": "5000+", "career_page_url": "https://www.airbus.com/careers/", "ats_provider": "Taleo"},
    {"name": "Allianz", "country": "DE", "city": "Munich", "industry": "Insurance", "size": "5000+", "career_page_url": "https://careers.allianz.com/", "ats_provider": "Workday"},
    {"name": "Bayer", "country": "DE", "city": "Leverkusen", "industry": "Pharma", "size": "5000+", "career_page_url": "https://www.bayer.com/en/careers", "ats_provider": "Workday"},
    {"name": "BMW", "country": "DE", "city": "Munich", "industry": "Automotive", "size": "5000+", "career_page_url": "https://www.bmwgroup.com/en/careers/", "ats_provider": "Taleo"},
    {"name": "Bosch", "country": "DE", "city": "Stuttgart", "industry": "Engineering", "size": "5000+", "career_page_url": "https://www.bosch.de/en/our-company/bosch-career/", "ats_provider": "Taleo"},
    {"name": "Checkout.com", "country": "DE", "city": "Berlin", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.checkout.com/careers#jobs", "ats_provider": "Greenhouse"},
    {"name": "Delivery Hero", "country": "DE", "city": "Berlin", "industry": "Food Delivery", "size": "5000+", "career_page_url": "https://www.deliveryhero.com/careers/", "ats_provider": "Workday"},
    {"name": "Deutsche Bank", "country": "DE", "city": "Frankfurt", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.db.com/careers/", "ats_provider": "Workday"},
    {"name": "Deutsche Telekom", "country": "DE", "city": "Bonn", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.telekom.com/en/careers", "ats_provider": "Workday"},
    {"name": "GitLab", "country": "DE", "city": "Berlin", "industry": "DevOps", "size": "201-1000", "career_page_url": "https://about.gitlab.com/jobs/", "ats_provider": "Greenhouse"},
    {"name": "HelloFresh", "country": "DE", "city": "Berlin", "industry": "Food", "size": "5000+", "career_page_url": "https://www.hellofreshgroup.com/en/careers", "ats_provider": "Greenhouse"},
    {"name": "Mercedes-Benz", "country": "DE", "city": "Stuttgart", "industry": "Automotive", "size": "5000+", "career_page_url": "https://group.mercedes-benz.com/careers/", "ats_provider": "Taleo"},
    {"name": "N26", "country": "DE", "city": "Berlin", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://n26.com/en-eu/careers", "ats_provider": "Greenhouse"},
    {"name": "SAP", "country": "DE", "city": "Walldorf", "industry": "Enterprise Software", "size": "5000+", "career_page_url": "https://jobs.sap.com/", "ats_provider": "SAP"},
    {"name": "Siemens", "country": "DE", "city": "Munich", "industry": "Engineering", "size": "5000+", "career_page_url": "https://jobs.siemens.com/", "ats_provider": "Taleo"},
    {"name": "SoundCloud", "country": "DE", "city": "Berlin", "industry": "Music", "size": "201-1000", "career_page_url": "https://careers.soundcloud.com/", "ats_provider": "Greenhouse"},
    {"name": "Spotify Germany", "country": "DE", "city": "Berlin", "industry": "Music", "size": "5000+", "career_page_url": "https://www.lifeatspotify.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Volkswagen", "country": "DE", "city": "Wolfsburg", "industry": "Automotive", "size": "5000+", "career_page_url": "https://www.volkswagen-karriere.de/", "ats_provider": "Taleo"},
    {"name": "Zalando", "country": "DE", "city": "Berlin", "industry": "E-commerce", "size": "5000+", "career_page_url": "https://jobs.zalando.com/", "ats_provider": "Workday"},
    # Netherlands
    {"name": "Adyen", "country": "NL", "city": "Amsterdam", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.adyen.com/careers", "ats_provider": "Greenhouse"},
    {"name": "Booking.com", "country": "NL", "city": "Amsterdam", "industry": "Travel", "size": "5000+", "career_page_url": "https://jobs.booking.com/", "ats_provider": "Workday"},
    {"name": "Bunq", "country": "NL", "city": "Amsterdam", "industry": "Fintech", "size": "201-1000", "career_page_url": "https://www.bunq.com/careers", "ats_provider": "Greenhouse"},
    {"name": "Databricks Netherlands", "country": "NL", "city": "Amsterdam", "industry": "Data", "size": "5000+", "career_page_url": "https://www.databricks.com/company/careers", "ats_provider": "Greenhouse"},
    {"name": "ING", "country": "NL", "city": "Amsterdam", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.ing.jobs/", "ats_provider": "Workday"},
    {"name": "Miro", "country": "NL", "city": "Amsterdam", "industry": "SaaS", "size": "1001-5000", "career_page_url": "https://miro.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Optiver", "country": "NL", "city": "Amsterdam", "industry": "Trading", "size": "1001-5000", "career_page_url": "https://www.optiver.com/working-at-optiver/", "ats_provider": "Greenhouse"},
    {"name": "Philips", "country": "NL", "city": "Amsterdam", "industry": "Health", "size": "5000+", "career_page_url": "https://www.careers.philips.com/", "ats_provider": "Workday"},
    {"name": "Picnic", "country": "NL", "city": "Amsterdam", "industry": "Food Delivery", "size": "1001-5000", "career_page_url": "https://picnic.app/careers", "ats_provider": "Greenhouse"},
    {"name": "Rabobank", "country": "NL", "city": "Utrecht", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.werkenbijrabobank.nl/", "ats_provider": "Workday"},
    {"name": "TomTom", "country": "NL", "city": "Amsterdam", "industry": "Navigation", "size": "1001-5000", "career_page_url": "https://www.tomtom.com/careers/", "ats_provider": "Workday"},
    {"name": "Uber Netherlands", "country": "NL", "city": "Amsterdam", "industry": "Tech", "size": "5000+", "career_page_url": "https://www.uber.com/global/en/careers/", "ats_provider": "Greenhouse"},
    # Sweden
    {"name": "Ericsson", "country": "SE", "city": "Stockholm", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.ericsson.com/en/careers", "ats_provider": "Taleo"},
    {"name": "IKEA", "country": "SE", "city": "Älmhult", "industry": "Retail", "size": "5000+", "career_page_url": "https://www.ikea.com/global/en/join-us/", "ats_provider": "Taleo"},
    {"name": "Klarna", "country": "SE", "city": "Stockholm", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.klarna.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "King", "country": "SE", "city": "Stockholm", "industry": "Gaming", "size": "1001-5000", "career_page_url": "https://careers.king.com/", "ats_provider": "Greenhouse"},
    {"name": "Northvolt", "country": "SE", "city": "Stockholm", "industry": "Energy", "size": "201-1000", "career_page_url": "https://northvolt.com/career/", "ats_provider": "Teamtailor"},
    {"name": "Spotify", "country": "SE", "city": "Stockholm", "industry": "Music", "size": "5000+", "career_page_url": "https://www.lifeatspotify.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Truecaller", "country": "SE", "city": "Stockholm", "industry": "Telecom", "size": "201-1000", "career_page_url": "https://career.truecaller.com/", "ats_provider": "Teamtailor"},
    {"name": "Volvo", "country": "SE", "city": "Gothenburg", "industry": "Automotive", "size": "5000+", "career_page_url": "https://www.volvogroup.com/en/careers.html", "ats_provider": "Taleo"},
    # Denmark
    {"name": "Maersk", "country": "DK", "city": "Copenhagen", "industry": "Shipping", "size": "5000+", "career_page_url": "https://www.maersk.com/careers", "ats_provider": "Workday"},
    {"name": "Novo Nordisk", "country": "DK", "city": "Bagsværd", "industry": "Pharma", "size": "5000+", "career_page_url": "https://www.novonordisk.com/careers/", "ats_provider": "Workday"},
    {"name": "Pandora", "country": "DK", "city": "Copenhagen", "industry": "Jewelry", "size": "5000+", "career_page_url": "https://www.pandoragroup.com/careers", "ats_provider": "Workday"},
    {"name": "Trustpilot", "country": "DK", "city": "Copenhagen", "industry": "SaaS", "size": "201-1000", "career_page_url": "https://business.trustpilot.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Unity", "country": "DK", "city": "Copenhagen", "industry": "Gaming", "size": "1001-5000", "career_page_url": "https://unity.com/careers", "ats_provider": "Greenhouse"},
    # Norway
    {"name": "Adevinta Norway", "country": "NO", "city": "Oslo", "industry": "Marketplaces", "size": "1001-5000", "career_page_url": "https://www.adevinta.com/careers/", "ats_provider": "Workday"},
    {"name": "DNB", "country": "NO", "city": "Oslo", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.dnb.no/en/career", "ats_provider": "Workday"},
    {"name": "Equinor", "country": "NO", "city": "Stavanger", "industry": "Energy", "size": "5000+", "career_page_url": "https://www.equinor.com/careers", "ats_provider": "Taleo"},
    {"name": "Kahoot!", "country": "NO", "city": "Oslo", "industry": "EdTech", "size": "201-1000", "career_page_url": "https://kahoot.com/jobs/", "ats_provider": "Greenhouse"},
    {"name": "Schibsted", "country": "NO", "city": "Oslo", "industry": "Media", "size": "1001-5000", "career_page_url": "https://www.schibsted.com/career/", "ats_provider": "Teamtailor"},
    {"name": "Telenor", "country": "NO", "city": "Oslo", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.telenor.com/careers/", "ats_provider": "Workday"},
    # Finland
    {"name": "Nokia", "country": "FI", "city": "Espoo", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.nokia.com/about-us/careers/", "ats_provider": "Workday"},
    {"name": "Supercell", "country": "FI", "city": "Helsinki", "industry": "Gaming", "size": "201-1000", "career_page_url": "https://supercell.com/en/careers/", "ats_provider": "Greenhouse"},
    {"name": "Wolt", "country": "FI", "city": "Helsinki", "industry": "Food Delivery", "size": "1001-5000", "career_page_url": "https://careers.wolt.com/", "ats_provider": "Greenhouse"},
    # Belgium
    {"name": "Deloitte Belgium", "country": "BE", "city": "Brussels", "industry": "Consulting", "size": "5000+", "career_page_url": "https://www2.deloitte.com/be/en/careers/", "ats_provider": "Taleo"},
    {"name": "ING Belgium", "country": "BE", "city": "Brussels", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.ing.jobs/", "ats_provider": "Workday"},
    {"name": "Showpad", "country": "BE", "city": "Ghent", "industry": "SaaS", "size": "201-1000", "career_page_url": "https://www.showpad.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Solvay", "country": "BE", "city": "Brussels", "industry": "Chemicals", "size": "5000+", "career_page_url": "https://careers.solvay.com/", "ats_provider": "Taleo"},
    {"name": "UiPath", "country": "BE", "city": "Brussels", "industry": "RPA", "size": "1001-5000", "career_page_url": "https://www.uipath.com/company/careers", "ats_provider": "Greenhouse"},
    # Luxembourg
    {"name": "Amazon Luxembourg", "country": "LU", "city": "Luxembourg", "industry": "Tech", "size": "5000+", "career_page_url": "https://www.amazon.jobs/en/locations/luxembourg-lux", "ats_provider": "Internal"},
    {"name": "Docler Holding", "country": "LU", "city": "Luxembourg", "industry": "Media", "size": "201-1000", "career_page_url": "https://www.doclerholding.com/careers", "ats_provider": "SmartRecruiters"},
    {"name": "SES", "country": "LU", "city": "Luxembourg", "industry": "Satellite", "size": "1001-5000", "career_page_url": "https://www.ses.com/careers", "ats_provider": "Taleo"},
    # Switzerland
    {"name": "ABB", "country": "CH", "city": "Zurich", "industry": "Engineering", "size": "5000+", "career_page_url": "https://global.abb/group/en/careers", "ats_provider": "Taleo"},
    {"name": "Credit Suisse", "country": "CH", "city": "Zurich", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.credit-suisse.com/careers", "ats_provider": "Workday"},
    {"name": "Google Switzerland", "country": "CH", "city": "Zurich", "industry": "Tech", "size": "5000+", "career_page_url": "https://careers.google.com/locations/zurich/", "ats_provider": "Internal"},
    {"name": "Nestlé", "country": "CH", "city": "Vevey", "industry": "Food", "size": "5000+", "career_page_url": "https://www.nestlejobs.com/", "ats_provider": "Taleo"},
    {"name": "Roche", "country": "CH", "city": "Basel", "industry": "Pharma", "size": "5000+", "career_page_url": "https://www.roche.com/careers", "ats_provider": "Workday"},
    {"name": "SAP Switzerland", "country": "CH", "city": "Zurich", "industry": "Enterprise Software", "size": "5000+", "career_page_url": "https://jobs.sap.com/", "ats_provider": "SAP"},
    {"name": "SIX", "country": "CH", "city": "Zurich", "industry": "Fintech", "size": "1001-5000", "career_page_url": "https://www.six-group.com/careers", "ats_provider": "Workday"},
    {"name": "Swisscom", "country": "CH", "city": "Bern", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.swisscom.ch/en/about/career/", "ats_provider": "Workday"},
    {"name": "UBS", "country": "CH", "city": "Zurich", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.ubs.com/global/en/careers.html", "ats_provider": "Workday"},
    {"name": "Zurich Insurance", "country": "CH", "city": "Zurich", "industry": "Insurance", "size": "5000+", "career_page_url": "https://www.zurich.com/en/careers", "ats_provider": "Workday"},
    # Austria
    {"name": "bwin", "country": "AT", "city": "Vienna", "industry": "Gaming", "size": "1001-5000", "career_page_url": "https://www.bwin.com/careers", "ats_provider": "Workday"},
    {"name": "Erste Group", "country": "AT", "city": "Vienna", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.erstegroup.com/careers", "ats_provider": "Workday"},
    {"name": "Raiffeisen Bank International", "country": "AT", "city": "Vienna", "industry": "Banking", "size": "5000+", "career_page_url": "https://jobs.rbinternational.com/", "ats_provider": "Workday"},
    {"name": "Red Bull", "country": "AT", "city": "Fuschl am See", "industry": "Beverages", "size": "1001-5000", "career_page_url": "https://www.redbull.com/int-en/jobs", "ats_provider": "Workday"},
    # France
    {"name": "Airbnb France", "country": "FR", "city": "Paris", "industry": "Travel", "size": "5000+", "career_page_url": "https://careers.airbnb.com/", "ats_provider": "Greenhouse"},
    {"name": "Blablacar", "country": "FR", "city": "Paris", "industry": "Travel", "size": "201-1000", "career_page_url": "https://www.blablacar.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "BNP Paribas", "country": "FR", "city": "Paris", "industry": "Banking", "size": "5000+", "career_page_url": "https://group.bnpparibas/careers", "ats_provider": "Taleo"},
    {"name": "BlaBlaCar", "country": "FR", "city": "Paris", "industry": "Travel", "size": "201-1000", "career_page_url": "https://www.blablacar.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Datadog", "country": "FR", "city": "Paris", "industry": "Observability", "size": "5000+", "career_page_url": "https://careers.datadoghq.com/", "ats_provider": "Greenhouse"},
    {"name": "Deezer", "country": "FR", "city": "Paris", "industry": "Music", "size": "201-1000", "career_page_url": "https://www.deezer.com/jobs", "ats_provider": "Greenhouse"},
    {"name": "Doctolib", "country": "FR", "city": "Paris", "industry": "Health", "size": "1001-5000", "career_page_url": "https://www.doctolib.fr/careers", "ats_provider": "Greenhouse"},
    {"name": "Ekimetrics", "country": "FR", "city": "Paris", "industry": "Consulting", "size": "201-1000", "career_page_url": "https://www.ekimetrics.com/careers", "ats_provider": "Greenhouse"},
    {"name": "L'Oréal", "country": "FR", "city": "Clichy", "industry": "Consumer Goods", "size": "5000+", "career_page_url": "https://careers.loreal.com/", "ats_provider": "Workday"},
    {"name": "Ledger", "country": "FR", "city": "Paris", "industry": "Crypto", "size": "201-1000", "career_page_url": "https://www.ledger.com/careers", "ats_provider": "Greenhouse"},
    {"name": "Michelin", "country": "FR", "city": "Clermont-Ferrand", "industry": "Automotive", "size": "5000+", "career_page_url": "https://careers.michelin.com/", "ats_provider": "Taleo"},
    {"name": "OVHcloud", "country": "FR", "city": "Roubaix", "industry": "Cloud", "size": "5000+", "career_page_url": "https://careers.ovhcloud.com/", "ats_provider": "Workday"},
    {"name": "Société Générale", "country": "FR", "city": "Paris", "industry": "Banking", "size": "5000+", "career_page_url": "https://careers.societegenerale.com/", "ats_provider": "Taleo"},
    {"name": "TotalEnergies", "country": "FR", "city": "Paris", "industry": "Energy", "size": "5000+", "career_page_url": "https://totalenergies.com/careers", "ats_provider": "Taleo"},
    # Poland
    {"name": "Allegro", "country": "PL", "city": "Poznan", "industry": "E-commerce", "size": "5000+", "career_page_url": "https://allegro.pl/praca", "ats_provider": "SmartRecruiters"},
    {"name": "CD Projekt Red", "country": "PL", "city": "Warsaw", "industry": "Gaming", "size": "1001-5000", "career_page_url": "https://jobs.cdprojektred.com/", "ats_provider": "Workday"},
    {"name": "Ericsson Poland", "country": "PL", "city": "Krakow", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.ericsson.com/en/careers", "ats_provider": "Taleo"},
    {"name": "ING Poland", "country": "PL", "city": "Warsaw", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.ing.jobs/", "ats_provider": "Workday"},
    {"name": "Nokia Poland", "country": "PL", "city": "Wroclaw", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.nokia.com/about-us/careers/", "ats_provider": "Workday"},
    {"name": "Siemens Poland", "country": "PL", "city": "Warsaw", "industry": "Engineering", "size": "5000+", "career_page_url": "https://jobs.siemens.com/", "ats_provider": "Taleo"},
    {"name": "SoftServe", "country": "PL", "city": "Wroclaw", "industry": "IT Services", "size": "5000+", "career_page_url": "https://careers.softserveinc.com/", "ats_provider": "Workday"},
    # Portugal
    {"name": "Critical Software", "country": "PT", "city": "Coimbra", "industry": "Software", "size": "201-1000", "career_page_url": "https://criticalsoftware.com/careers", "ats_provider": "Teamtailor"},
    {"name": "Farfetch Portugal", "country": "PT", "city": "Lisbon", "industry": "E-commerce", "size": "1001-5000", "career_page_url": "https://aboutfarfetch.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "OutSystems", "country": "PT", "city": "Lisbon", "industry": "Low-code", "size": "1001-5000", "career_page_url": "https://www.outsystems.com/careers/", "ats_provider": "Workday"},
    {"name": "Talkdesk", "country": "PT", "city": "Lisbon", "industry": "SaaS", "size": "1001-5000", "career_page_url": "https://www.talkdesk.com/careers/", "ats_provider": "Greenhouse"},
    {"name": "Unbabel", "country": "PT", "city": "Lisbon", "industry": "AI", "size": "201-1000", "career_page_url": "https://unbabel.com/careers/", "ats_provider": "Greenhouse"},
    # Spain
    {"name": "BBVA", "country": "ES", "city": "Madrid", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.bbva.com/en/sustainability/talent/", "ats_provider": "Workday"},
    {"name": "Cabify", "country": "ES", "city": "Madrid", "industry": "Mobility", "size": "1001-5000", "career_page_url": "https://cabify.com/en/jobs", "ats_provider": "Greenhouse"},
    {"name": "Glovo", "country": "ES", "city": "Barcelona", "industry": "Delivery", "size": "1001-5000", "career_page_url": "https://jobs.glovoapp.com/", "ats_provider": "Greenhouse"},
    {"name": "Santander", "country": "ES", "city": "Madrid", "industry": "Banking", "size": "5000+", "career_page_url": "https://www.santander.com/en/careers", "ats_provider": "Workday"},
    {"name": "Telefónica", "country": "ES", "city": "Madrid", "industry": "Telecom", "size": "5000+", "career_page_url": "https://www.telefonica.com/en/communication-room/people/", "ats_provider": "Workday"},
    {"name": "Wallapop", "country": "ES", "city": "Barcelona", "industry": "Marketplace", "size": "201-1000", "career_page_url": "https://jobs.wallapop.com/", "ats_provider": "Greenhouse"},
]

COUNTRY_CITIES = {
    "GB": ["London", "Manchester", "Birmingham", "Edinburgh", "Bristol", "Cambridge", "Leeds", "Glasgow"],
    "IE": ["Dublin", "Cork", "Galway", "Limerick"],
    "DE": ["Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt", "Stuttgart", "Dusseldorf", "Leipzig"],
    "NL": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"],
    "SE": ["Stockholm", "Gothenburg", "Malmö", "Uppsala"],
    "DK": ["Copenhagen", "Aarhus", "Odense"],
    "NO": ["Oslo", "Bergen", "Trondheim", "Stavanger"],
    "FI": ["Helsinki", "Espoo", "Tampere", "Turku"],
    "BE": ["Brussels", "Antwerp", "Ghent", "Leuven"],
    "LU": ["Luxembourg", "Esch-sur-Alzette"],
    "CH": ["Zurich", "Geneva", "Basel", "Bern", "Lausanne"],
    "AT": ["Vienna", "Graz", "Linz", "Salzburg"],
    "FR": ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Lille"],
    "PL": ["Warsaw", "Krakow", "Wroclaw", "Gdansk", "Poznan", "Lodz"],
    "PT": ["Lisbon", "Porto", "Coimbra", "Braga"],
    "ES": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Malaga"],
}

INDUSTRIES = [
    "Fintech", "SaaS", "E-commerce", "Cloud", "Telecom", "Banking", "Gaming", "Health",
    "Mobility", "Energy", "Media", "Insurance", "Automotive", "Consulting", "Enterprise Software",
    "Pharma", "Cybersecurity", "AI", "Travel", "Logistics", "EdTech", "Marketplace", "Crypto"
]

ATS_PROVIDERS = ["Greenhouse", "Lever", "Ashby", "Workday", "SmartRecruiters", "Teamtailor", "Personio", "SAP", "Taleo", "Internal", "Unknown"]

SIZES = ["1-50", "51-200", "201-1000", "1001-5000", "5000+"]

VISA_LIKELIHOOD = {"Likely": 0.35, "Unknown": 0.50, "Yes": 0.10, "No": 0.05}


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace(",", "").replace("/", "-")[:64]


def _weighted_choice(choices: dict) -> str:
    import random

    total = sum(choices.values())
    r = random.uniform(0, total)
    upto = 0.0
    for choice, weight in choices.items():
        upto += weight
        if upto >= r:
            return choice
    return list(choices.keys())[-1]


def generate_companies() -> list[dict]:
    """Return only the curated list of real European companies.

    The previous version generated synthetic placeholder companies. Those have
    been removed so the database only contains real employers.
    """
    import random

    companies = []
    seen_slugs = set()

    for entry in KNOWN_COMPANIES:
        entry = dict(entry)
        entry["slug"] = _slugify(entry["name"])
        if entry["slug"] in seen_slugs:
            entry["slug"] = f"{entry['slug']}-{len(seen_slugs)}"
        seen_slugs.add(entry["slug"])
        entry.setdefault("visa_sponsorship", _weighted_choice(VISA_LIKELIHOOD))
        entry.setdefault("relocation_assistance", random.random() < 0.3)
        entry.setdefault("remote_policy", random.choice(["remote-first", "hybrid", "office-first", "fully remote"]))
        entry.setdefault("remote_friendly", entry.get("remote_policy") in ("remote-first", "fully remote"))
        entry.setdefault("hiring_status", "active")
        entry.setdefault("is_active", True)
        entry.setdefault("ats_config", {})
        if entry.get("career_page_url") and not entry.get("website"):
            entry["website"] = entry["career_page_url"]
        entry.setdefault("known_tech_stack", [])
        entry.setdefault("public_tech_stack", [])
        entry.setdefault("engineering_blog_url", None)
        entry.setdefault("ats_changes", 0)
        entry.setdefault("jobs_found", 0)
        companies.append(entry)

    return companies


def write_seed_file():
    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    companies = generate_companies()
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        json.dump({"companies": companies}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(companies)} real companies to {SEED_FILE}")


def seed_countries(session):
    country_data = [
        ("United Kingdom", "GB", "Western Europe", False),
        ("Ireland", "IE", "Western Europe", True),
        ("Germany", "DE", "Western Europe", True),
        ("Netherlands", "NL", "Western Europe", True),
        ("Sweden", "SE", "Northern Europe", True),
        ("Denmark", "DK", "Northern Europe", True),
        ("Norway", "NO", "Northern Europe", False),
        ("Finland", "FI", "Northern Europe", True),
        ("Belgium", "BE", "Western Europe", True),
        ("Luxembourg", "LU", "Western Europe", True),
        ("Switzerland", "CH", "Western Europe", False),
        ("Austria", "AT", "Western Europe", True),
        ("France", "FR", "Western Europe", True),
        ("Poland", "PL", "Eastern Europe", True),
        ("Portugal", "PT", "Southern Europe", True),
        ("Spain", "ES", "Southern Europe", True),
    ]
    for name, code, region, is_eu in country_data:
        existing = session.execute(select(Country).where(Country.code == code)).scalar_one_or_none()
        if not existing:
            session.add(Country(name=name, code=code, region=region, is_eu=is_eu))
    session.commit()


def seed_companies(session):
    if not SEED_FILE.exists():
        write_seed_file()

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    country_map = {c.code: c.id for c in session.execute(select(Country)).scalars().all()}

    added = 0
    now = datetime.utcnow()
    for entry in data["companies"]:
        existing = session.execute(
            select(Company).where(Company.slug == entry["slug"])
        ).scalar_one_or_none()
        if existing:
            continue

        company = Company(
            name=entry["name"],
            slug=entry["slug"],
            description=entry.get("description"),
            website=entry.get("website"),
            career_page_url=entry.get("career_page_url"),
            engineering_blog_url=entry.get("engineering_blog_url"),
            ats_provider=entry.get("ats_provider"),
            ats_config=entry.get("ats_config", {}),
            ats_changes=entry.get("ats_changes", 0),
            industry=entry.get("industry"),
            size=entry.get("size"),
            country_id=country_map.get(entry["country"]),
            city=entry.get("city"),
            employee_count=entry.get("employee_count"),
            visa_sponsorship=entry.get("visa_sponsorship", "Unknown"),
            relocation_assistance=entry.get("relocation_assistance", False),
            remote_policy=entry.get("remote_policy"),
            remote_friendly=entry.get("remote_friendly", False),
            hiring_status=entry.get("hiring_status", "active"),
            is_active=entry.get("is_active", True),
            glassdoor_rating=entry.get("glassdoor_rating"),
            known_tech_stack=entry.get("known_tech_stack", []),
            public_tech_stack=entry.get("public_tech_stack", []),
            first_seen=now,
            last_seen=now,
            last_crawled=None,
            jobs_found=entry.get("jobs_found", 0),
        )
        session.add(company)
        added += 1
        if added % 100 == 0:
            session.commit()

    session.commit()
    print(f"Added {added} new real companies. Total in DB may be higher if already seeded.")


def main():
    from app.db.base import Base  # noqa

    Base.metadata.create_all(bind=sync_engine)

    session = SessionLocal()
    try:
        seed_countries(session)
        seed_companies(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
