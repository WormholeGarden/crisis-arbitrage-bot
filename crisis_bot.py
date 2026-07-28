#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE BOT - v1.0
Real-time crisis arbitrage trading bot based on FSI 2024 and WST theory.
Author: GCIN Trading Systems
License: MIT
"""

import random
import time
from typing import Dict, List, Optional

# ─── DATA ──────────────────────────────────────────────────────────────

FSI_2024 = {
    "SOM": {"name": "Somalia", "flag": "🇸🇴", "fsi_score": 111.3, "rank": 1, "region": "africa"},
    "SDN": {"name": "Sudan", "flag": "🇸🇩", "fsi_score": 109.3, "rank": 2, "region": "africa"},
    "SSD": {"name": "South Sudan", "flag": "🇸🇸", "fsi_score": 109.0, "rank": 3, "region": "africa"},
    "SYR": {"name": "Syria", "flag": "🇸🇾", "fsi_score": 108.1, "rank": 4, "region": "middleeast"},
    "COD": {"name": "Congo-Kinshasa", "flag": "🇨🇩", "fsi_score": 106.7, "rank": 5, "region": "africa"},
    "YEM": {"name": "Yemen", "flag": "🇾🇪", "fsi_score": 106.6, "rank": 6, "region": "middleeast"},
    "AFG": {"name": "Afghanistan", "flag": "🇦🇫", "fsi_score": 103.9, "rank": 7, "region": "asia"},
    "CAF": {"name": "Central African Rep.", "flag": "🇨🇫", "fsi_score": 103.9, "rank": 8, "region": "africa"},
    "HTI": {"name": "Haiti", "flag": "🇭🇹", "fsi_score": 103.5, "rank": 9, "region": "americas"},
    "TCD": {"name": "Chad", "flag": "🇹🇩", "fsi_score": 102.7, "rank": 10, "region": "africa"},
    "MMR": {"name": "Myanmar", "flag": "🇲🇲", "fsi_score": 100.0, "rank": 11, "region": "asia"},
    "ETH": {"name": "Ethiopia", "flag": "🇪🇹", "fsi_score": 98.1, "rank": 12, "region": "africa"},
    "PSE": {"name": "Palestine", "flag": "🇵🇸", "fsi_score": 97.8, "rank": 13, "region": "middleeast"},
    "MLI": {"name": "Mali", "flag": "🇲🇱", "fsi_score": 97.3, "rank": 14, "region": "africa"},
    "NGA": {"name": "Nigeria", "flag": "🇳🇬", "fsi_score": 96.6, "rank": 15, "region": "africa"},
    "LBY": {"name": "Libya", "flag": "🇱🇾", "fsi_score": 96.5, "rank": 16, "region": "africa"},
    "GIN": {"name": "Guinea", "flag": "🇬🇳", "fsi_score": 96.4, "rank": 17, "region": "africa"},
    "ZWE": {"name": "Zimbabwe", "flag": "🇿🇼", "fsi_score": 95.7, "rank": 18, "region": "africa"},
    "NER": {"name": "Niger", "flag": "🇳🇪", "fsi_score": 95.2, "rank": 19, "region": "africa"},
    "CMR": {"name": "Cameroon", "flag": "🇨🇲", "fsi_score": 94.3, "rank": 20, "region": "africa"},
    "BFA": {"name": "Burkina Faso", "flag": "🇧🇫", "fsi_score": 94.2, "rank": 21, "region": "africa"},
    "UKR": {"name": "Ukraine", "flag": "🇺🇦", "fsi_score": 93.1, "rank": 22, "region": "europe"},
    "LBN": {"name": "Lebanon", "flag": "🇱🇧", "fsi_score": 92.7, "rank": 23, "region": "middleeast"},
    "BDI": {"name": "Burundi", "flag": "🇧🇮", "fsi_score": 92.6, "rank": 24, "region": "africa"},
    "MOZ": {"name": "Mozambique", "flag": "🇲🇿", "fsi_score": 92.5, "rank": 25, "region": "africa"},
    "ERI": {"name": "Eritrea", "flag": "🇪🇷", "fsi_score": 92.1, "rank": 26, "region": "africa"},
    "PAK": {"name": "Pakistan", "flag": "🇵🇰", "fsi_score": 91.7, "rank": 27, "region": "asia"},
    "UGA": {"name": "Uganda", "flag": "🇺🇬", "fsi_score": 91.1, "rank": 28, "region": "africa"},
    "COG": {"name": "Congo-Brazzaville", "flag": "🇨🇬", "fsi_score": 90.2, "rank": 29, "region": "africa"},
    "VEN": {"name": "Venezuela", "flag": "🇻🇪", "fsi_score": 89.0, "rank": 30, "region": "americas"},
    "IRQ": {"name": "Iraq", "flag": "🇮🇶", "fsi_score": 88.6, "rank": 31, "region": "middleeast"},
    "GNB": {"name": "Guinea-Bissau", "flag": "🇬🇼", "fsi_score": 88.4, "rank": 32, "region": "africa"},
    "LKA": {"name": "Sri Lanka", "flag": "🇱🇰", "fsi_score": 88.2, "rank": 33, "region": "asia"},
    "MRT": {"name": "Mauritania", "flag": "🇲🇷", "fsi_score": 87.0, "rank": 34, "region": "africa"},
    "LBR": {"name": "Liberia", "flag": "🇱🇷", "fsi_score": 86.9, "rank": 35, "region": "africa"},
    "KEN": {"name": "Kenya", "flag": "🇰🇪", "fsi_score": 86.5, "rank": 36, "region": "africa"},
    "BGD": {"name": "Bangladesh", "flag": "🇧🇩", "fsi_score": 85.9, "rank": 37, "region": "asia"},
    "AGO": {"name": "Angola", "flag": "🇦🇴", "fsi_score": 85.6, "rank": 38, "region": "africa"},
    "CIV": {"name": "Ivory Coast", "flag": "🇨🇮", "fsi_score": 85.3, "rank": 39, "region": "africa"},
    "PRK": {"name": "North Korea", "flag": "🇰🇵", "fsi_score": 84.9, "rank": 40, "region": "asia"},
    "TUR": {"name": "Turkey", "flag": "🇹🇷", "fsi_score": 84.0, "rank": 41, "region": "europe"},
    "GNQ": {"name": "Equatorial Guinea", "flag": "🇬🇶", "fsi_score": 83.7, "rank": 42, "region": "africa"},
    "IRN": {"name": "Iran", "flag": "🇮🇷", "fsi_score": 82.9, "rank": 43, "region": "middleeast"},
    "EGY": {"name": "Egypt", "flag": "🇪🇬", "fsi_score": 82.8, "rank": 44, "region": "africa"},
    "SLE": {"name": "Sierra Leone", "flag": "🇸🇱", "fsi_score": 82.6, "rank": 45, "region": "africa"},
    "RWA": {"name": "Rwanda", "flag": "🇷🇼", "fsi_score": 81.8, "rank": 46, "region": "africa"},
    "COM": {"name": "Comoros", "flag": "🇰🇲", "fsi_score": 81.7, "rank": 47, "region": "africa"},
    "DJI": {"name": "Djibouti", "flag": "🇩🇯", "fsi_score": 81.6, "rank": 48, "region": "africa"},
    "RUS": {"name": "Russia", "flag": "🇷🇺", "fsi_score": 81.6, "rank": 48, "region": "europe"},
    "ZMB": {"name": "Zambia", "flag": "🇿🇲", "fsi_score": 81.2, "rank": 50, "region": "africa"},
    "TGO": {"name": "Togo", "flag": "🇹🇬", "fsi_score": 81.1, "rank": 51, "region": "africa"},
    "MWI": {"name": "Malawi", "flag": "🇲🇼", "fsi_score": 80.5, "rank": 52, "region": "africa"},
    "MDG": {"name": "Madagascar", "flag": "🇲🇬", "fsi_score": 79.8, "rank": 53, "region": "africa"},
    "PNG": {"name": "Papua New Guinea", "flag": "🇵🇬", "fsi_score": 78.8, "rank": 54, "region": "oceania"},
    "KHM": {"name": "Cambodia", "flag": "🇰🇭", "fsi_score": 78.6, "rank": 55, "region": "asia"},
    "HND": {"name": "Honduras", "flag": "🇭🇳", "fsi_score": 78.1, "rank": 56, "region": "americas"},
    "NPL": {"name": "Nepal", "flag": "🇳🇵", "fsi_score": 78.0, "rank": 57, "region": "asia"},
    "SWZ": {"name": "Eswatini", "flag": "🇸🇿", "fsi_score": 77.6, "rank": 58, "region": "africa"},
    "SLB": {"name": "Solomon Islands", "flag": "🇸🇧", "fsi_score": 77.6, "rank": 58, "region": "oceania"},
    "NIC": {"name": "Nicaragua", "flag": "🇳🇮", "fsi_score": 76.7, "rank": 60, "region": "americas"},
    "GMB": {"name": "Gambia", "flag": "🇬🇲", "fsi_score": 76.1, "rank": 61, "region": "africa"},
    "TZA": {"name": "Tanzania", "flag": "🇹🇿", "fsi_score": 75.7, "rank": 62, "region": "africa"},
    "COL": {"name": "Colombia", "flag": "🇨🇴", "fsi_score": 75.6, "rank": 63, "region": "americas"},
    "PHL": {"name": "Philippines", "flag": "🇵🇭", "fsi_score": 75.1, "rank": 64, "region": "asia"},
    "GTM": {"name": "Guatemala", "flag": "🇬🇹", "fsi_score": 74.9, "rank": 65, "region": "americas"},
    "KGZ": {"name": "Kyrgyzstan", "flag": "🇰🇬", "fsi_score": 74.9, "rank": 65, "region": "asia"},
    "TLS": {"name": "East Timor", "flag": "🇹🇱", "fsi_score": 74.8, "rank": 67, "region": "asia"},
    "LSO": {"name": "Lesotho", "flag": "🇱🇸", "fsi_score": 74.6, "rank": 68, "region": "africa"},
    "JOR": {"name": "Jordan", "flag": "🇯🇴", "fsi_score": 74.3, "rank": 69, "region": "middleeast"},
    "SEN": {"name": "Senegal", "flag": "🇸🇳", "fsi_score": 74.2, "rank": 70, "region": "africa"},
    "LAO": {"name": "Laos", "flag": "🇱🇦", "fsi_score": 73.8, "rank": 71, "region": "asia"},
    "AZE": {"name": "Azerbaijan", "flag": "🇦🇿", "fsi_score": 72.8, "rank": 72, "region": "asia"},
    "TJK": {"name": "Tajikistan", "flag": "🇹🇯", "fsi_score": 72.8, "rank": 72, "region": "asia"},
    "BEN": {"name": "Benin", "flag": "🇧🇯", "fsi_score": 72.5, "rank": 74, "region": "africa"},
    "IND": {"name": "India", "flag": "🇮🇳", "fsi_score": 72.3, "rank": 75, "region": "asia"},
    "PER": {"name": "Peru", "flag": "🇵🇪", "fsi_score": 72.0, "rank": 76, "region": "americas"},
    "BIH": {"name": "Bosnia-Herzegovina", "flag": "🇧🇦", "fsi_score": 71.0, "rank": 77, "region": "europe"},
    "BRA": {"name": "Brazil", "flag": "🇧🇷", "fsi_score": 70.3, "rank": 78, "region": "americas"},
    "GAB": {"name": "Gabon", "flag": "🇬🇦", "fsi_score": 70.2, "rank": 79, "region": "africa"},
    "ZAF": {"name": "South Africa", "flag": "🇿🇦", "fsi_score": 69.6, "rank": 80, "region": "africa"},
    "BOL": {"name": "Bolivia", "flag": "🇧🇴", "fsi_score": 69.4, "rank": 81, "region": "americas"},
    "GEO": {"name": "Georgia", "flag": "🇬🇪", "fsi_score": 69.3, "rank": 82, "region": "asia"},
    "MEX": {"name": "Mexico", "flag": "🇲🇽", "fsi_score": 69.0, "rank": 83, "region": "americas"},
    "MAR": {"name": "Morocco", "flag": "🇲🇦", "fsi_score": 68.8, "rank": 84, "region": "africa"},
    "BLR": {"name": "Belarus", "flag": "🇧🇾", "fsi_score": 68.7, "rank": 85, "region": "europe"},
    "SLV": {"name": "El Salvador", "flag": "🇸🇻", "fsi_score": 68.7, "rank": 85, "region": "americas"},
    "DZA": {"name": "Algeria", "flag": "🇩🇿", "fsi_score": 68.6, "rank": 87, "region": "africa"},
    "STP": {"name": "Sao Tome and Principe", "flag": "🇸🇹", "fsi_score": 68.5, "rank": 88, "region": "africa"},
    "ARM": {"name": "Armenia", "flag": "🇦🇲", "fsi_score": 68.1, "rank": 89, "region": "asia"},
    "ECU": {"name": "Ecuador", "flag": "🇪🇨", "fsi_score": 68.0, "rank": 90, "region": "americas"},
    "SRB": {"name": "Serbia", "flag": "🇷🇸", "fsi_score": 67.8, "rank": 91, "region": "europe"},
    "TUN": {"name": "Tunisia", "flag": "🇹🇳", "fsi_score": 67.2, "rank": 92, "region": "africa"},
    "FSM": {"name": "F.S. Micronesia", "flag": "🇫🇲", "fsi_score": 66.9, "rank": 93, "region": "oceania"},
    "FJI": {"name": "Fiji", "flag": "🇫🇯", "fsi_score": 66.4, "rank": 94, "region": "oceania"},
    "THA": {"name": "Thailand", "flag": "🇹🇭", "fsi_score": 66.2, "rank": 95, "region": "asia"},
    "UZB": {"name": "Uzbekistan", "flag": "🇺🇿", "fsi_score": 64.8, "rank": 96, "region": "asia"},
    "MDA": {"name": "Moldova", "flag": "🇲🇩", "fsi_score": 64.7, "rank": 97, "region": "europe"},
    "BTN": {"name": "Bhutan", "flag": "🇧🇹", "fsi_score": 64.5, "rank": 98, "region": "asia"},
    "CHN": {"name": "China", "flag": "🇨🇳", "fsi_score": 64.4, "rank": 99, "region": "asia"},
    "BHR": {"name": "Bahrain", "flag": "🇧🇭", "fsi_score": 64.2, "rank": 100, "region": "middleeast"},
    "WSM": {"name": "Samoa", "flag": "🇼🇸", "fsi_score": 63.9, "rank": 101, "region": "oceania"},
    "IDN": {"name": "Indonesia", "flag": "🇮🇩", "fsi_score": 63.7, "rank": 102, "region": "asia"},
    "SAU": {"name": "Saudi Arabia", "flag": "🇸🇦", "fsi_score": 63.2, "rank": 103, "region": "middleeast"},
    "TKM": {"name": "Turkmenistan", "flag": "🇹🇲", "fsi_score": 62.2, "rank": 104, "region": "asia"},
    "PRY": {"name": "Paraguay", "flag": "🇵🇾", "fsi_score": 61.5, "rank": 105, "region": "americas"},
    "GHA": {"name": "Ghana", "flag": "🇬🇭", "fsi_score": 60.8, "rank": 106, "region": "africa"},
    "MDV": {"name": "Maldives", "flag": "🇲🇻", "fsi_score": 60.3, "rank": 107, "region": "asia"},
    "DOM": {"name": "Dominican Republic", "flag": "🇩🇴", "fsi_score": 60.2, "rank": 108, "region": "americas"},
    "JAM": {"name": "Jamaica", "flag": "🇯🇲", "fsi_score": 59.3, "rank": 109, "region": "americas"},
    "NAM": {"name": "Namibia", "flag": "🇳🇦", "fsi_score": 59.3, "rank": 109, "region": "africa"},
    "GUY": {"name": "Guyana", "flag": "🇬🇾", "fsi_score": 59.2, "rank": 111, "region": "americas"},
    "CUB": {"name": "Cuba", "flag": "🇨🇺", "fsi_score": 59.1, "rank": 112, "region": "americas"},
    "SUR": {"name": "Suriname", "flag": "🇸🇷", "fsi_score": 58.8, "rank": 113, "region": "americas"},
    "MKD": {"name": "North Macedonia", "flag": "🇲🇰", "fsi_score": 58.1, "rank": 114, "region": "europe"},
    "KAZ": {"name": "Kazakhstan", "flag": "🇰🇿", "fsi_score": 57.8, "rank": 115, "region": "asia"},
    "CPV": {"name": "Cape Verde", "flag": "🇨🇻", "fsi_score": 57.2, "rank": 116, "region": "africa"},
    "BLZ": {"name": "Belize", "flag": "🇧🇿", "fsi_score": 57.0, "rank": 117, "region": "americas"},
    "MNE": {"name": "Montenegro", "flag": "🇲🇪", "fsi_score": 56.9, "rank": 118, "region": "europe"},
    "VNM": {"name": "Vietnam", "flag": "🇻🇳", "fsi_score": 56.2, "rank": 119, "region": "asia"},
    "ALB": {"name": "Albania", "flag": "🇦🇱", "fsi_score": 55.9, "rank": 120, "region": "europe"},
    "GRC": {"name": "Greece", "flag": "🇬🇷", "fsi_score": 54.7, "rank": 121, "region": "europe"},
    "CYP": {"name": "Cyprus", "flag": "🇨🇾", "fsi_score": 54.1, "rank": 122, "region": "europe"},
    "BRN": {"name": "Brunei", "flag": "🇧🇳", "fsi_score": 53.9, "rank": 123, "region": "asia"},
    "BWA": {"name": "Botswana", "flag": "🇧🇼", "fsi_score": 53.6, "rank": 124, "region": "africa"},
    "TTO": {"name": "Trinidad and Tobago", "flag": "🇹🇹", "fsi_score": 53.5, "rank": 125, "region": "americas"},
    "MYS": {"name": "Malaysia", "flag": "🇲🇾", "fsi_score": 53.1, "rank": 126, "region": "asia"},
    "ATG": {"name": "Antigua and Barbuda", "flag": "🇦🇬", "fsi_score": 51.9, "rank": 127, "region": "americas"},
    "GRD": {"name": "Grenada", "flag": "🇬🇩", "fsi_score": 51.9, "rank": 127, "region": "americas"},
    "ISR": {"name": "Israel", "flag": "🇮🇱", "fsi_score": 51.5, "rank": 129, "region": "middleeast"},
    "ROU": {"name": "Romania", "flag": "🇷🇴", "fsi_score": 51.0, "rank": 130, "region": "europe"},
    "SYC": {"name": "Seychelles", "flag": "🇸🇨", "fsi_score": 51.0, "rank": 130, "region": "africa"},
    "MNG": {"name": "Mongolia", "flag": "🇲🇳", "fsi_score": 50.7, "rank": 132, "region": "asia"},
    "BGR": {"name": "Bulgaria", "flag": "🇧🇬", "fsi_score": 49.4, "rank": 133, "region": "europe"},
    "KWT": {"name": "Kuwait", "flag": "🇰🇼", "fsi_score": 49.3, "rank": 134, "region": "middleeast"},
    "BHS": {"name": "Bahamas", "flag": "🇧🇸", "fsi_score": 48.0, "rank": 135, "region": "americas"},
    "PAN": {"name": "Panama", "flag": "🇵🇦", "fsi_score": 47.7, "rank": 136, "region": "americas"},
    "OMN": {"name": "Oman", "flag": "🇴🇲", "fsi_score": 47.4, "rank": 137, "region": "middleeast"},
    "HUN": {"name": "Hungary", "flag": "🇭🇺", "fsi_score": 46.2, "rank": 138, "region": "europe"},
    "HRV": {"name": "Croatia", "flag": "🇭🇷", "fsi_score": 45.9, "rank": 139, "region": "europe"},
    "BRB": {"name": "Barbados", "flag": "🇧🇧", "fsi_score": 44.7, "rank": 140, "region": "americas"},
    "USA": {"name": "United States", "flag": "🇺🇸", "fsi_score": 44.5, "rank": 141, "region": "americas"},
    "ARG": {"name": "Argentina", "flag": "🇦🇷", "fsi_score": 44.2, "rank": 142, "region": "americas"},
    "ESP": {"name": "Spain", "flag": "🇪🇸", "fsi_score": 44.0, "rank": 143, "region": "europe"},
    "POL": {"name": "Poland", "flag": "🇵🇱", "fsi_score": 41.7, "rank": 144, "region": "europe"},
    "LVA": {"name": "Latvia", "flag": "🇱🇻", "fsi_score": 41.4, "rank": 145, "region": "europe"},
    "CHL": {"name": "Chile", "flag": "🇨🇱", "fsi_score": 41.1, "rank": 146, "region": "americas"},
    "ITA": {"name": "Italy", "flag": "🇮🇹", "fsi_score": 41.1, "rank": 146, "region": "europe"},
    "GBR": {"name": "United Kingdom", "flag": "🇬🇧", "fsi_score": 40.8, "rank": 148, "region": "europe"},
    "QAT": {"name": "Qatar", "flag": "🇶🇦", "fsi_score": 39.8, "rank": 149, "region": "middleeast"},
    "CRI": {"name": "Costa Rica", "flag": "🇨🇷", "fsi_score": 39.4, "rank": 150, "region": "americas"},
    "MUS": {"name": "Mauritius", "flag": "🇲🇺", "fsi_score": 37.8, "rank": 151, "region": "africa"},
    "CZE": {"name": "Czech Republic", "flag": "🇨🇿", "fsi_score": 37.7, "rank": 152, "region": "europe"},
    "LTU": {"name": "Lithuania", "flag": "🇱🇹", "fsi_score": 37.4, "rank": 153, "region": "europe"},
    "EST": {"name": "Estonia", "flag": "🇪🇪", "fsi_score": 36.5, "rank": 154, "region": "europe"},
    "SVK": {"name": "Slovakia", "flag": "🇸🇰", "fsi_score": 35.3, "rank": 155, "region": "europe"},
    "ARE": {"name": "United Arab Emirates", "flag": "🇦🇪", "fsi_score": 34.7, "rank": 156, "region": "middleeast"},
    "URY": {"name": "Uruguay", "flag": "🇺🇾", "fsi_score": 33.7, "rank": 157, "region": "americas"},
    "MLT": {"name": "Malta", "flag": "🇲🇹", "fsi_score": 31.1, "rank": 158, "region": "europe"},
    "BEL": {"name": "Belgium", "flag": "🇧🇪", "fsi_score": 30.3, "rank": 159, "region": "europe"},
    "JPN": {"name": "Japan", "flag": "🇯🇵", "fsi_score": 30.2, "rank": 160, "region": "asia"},
    "KOR": {"name": "South Korea", "flag": "🇰🇷", "fsi_score": 29.8, "rank": 161, "region": "asia"},
    "FRA": {"name": "France", "flag": "🇫🇷", "fsi_score": 28.3, "rank": 162, "region": "europe"},
    "SVN": {"name": "Slovenia", "flag": "🇸🇮", "fsi_score": 26.1, "rank": 163, "region": "europe"},
    "PRT": {"name": "Portugal", "flag": "🇵🇹", "fsi_score": 25.9, "rank": 164, "region": "europe"},
    "SGP": {"name": "Singapore", "flag": "🇸🇬", "fsi_score": 25.4, "rank": 165, "region": "asia"},
    "DEU": {"name": "Germany", "flag": "🇩🇪", "fsi_score": 24.0, "rank": 166, "region": "europe"},
    "AUT": {"name": "Austria", "flag": "🇦🇹", "fsi_score": 23.1, "rank": 167, "region": "europe"},
    "SWE": {"name": "Sweden", "flag": "🇸🇪", "fsi_score": 20.6, "rank": 168, "region": "europe"},
    "AUS": {"name": "Australia", "flag": "🇦🇺", "fsi_score": 19.6, "rank": 169, "region": "oceania"},
    "NLD": {"name": "Netherlands", "flag": "🇳🇱", "fsi_score": 19.5, "rank": 170, "region": "europe"},
    "LUX": {"name": "Luxembourg", "flag": "🇱🇺", "fsi_score": 18.7, "rank": 171, "region": "europe"},
    "CAN": {"name": "Canada", "flag": "🇨🇦", "fsi_score": 18.6, "rank": 172, "region": "americas"},
    "IRL": {"name": "Ireland", "flag": "🇮🇪", "fsi_score": 18.6, "rank": 172, "region": "europe"},
    "CHE": {"name": "Switzerland", "flag": "🇨🇭", "fsi_score": 16.2, "rank": 174, "region": "europe"},
    "DNK": {"name": "Denmark", "flag": "🇩🇰", "fsi_score": 15.9, "rank": 175, "region": "europe"},
    "NZL": {"name": "New Zealand", "flag": "🇳🇿", "fsi_score": 15.9, "rank": 175, "region": "oceania"},
    "ISL": {"name": "Iceland", "flag": "🇮🇸", "fsi_score": 15.2, "rank": 177, "region": "europe"},
    "FIN": {"name": "Finland", "flag": "🇫🇮", "fsi_score": 14.3, "rank": 178, "region": "europe"},
    "NOR": {"name": "Norway", "flag": "🇳🇴", "fsi_score": 12.7, "rank": 179, "region": "europe"},
}

WST_CLASSIFICATION = {
    # Core Nations
    "USA": {"class": "Core", "recovery_rate": 0.85},
    "GBR": {"class": "Core", "recovery_rate": 0.80},
    "DEU": {"class": "Core", "recovery_rate": 0.82},
    "FRA": {"class": "Core", "recovery_rate": 0.78},
    "JPN": {"class": "Core", "recovery_rate": 0.75},
    "CAN": {"class": "Core", "recovery_rate": 0.82},
    "AUS": {"class": "Core", "recovery_rate": 0.80},
    "CHE": {"class": "Core", "recovery_rate": 0.88},
    "NLD": {"class": "Core", "recovery_rate": 0.82},
    "NOR": {"class": "Core", "recovery_rate": 0.90},
    "SWE": {"class": "Core", "recovery_rate": 0.85},
    "DNK": {"class": "Core", "recovery_rate": 0.85},
    "FIN": {"class": "Core", "recovery_rate": 0.80},
    "IRL": {"class": "Core", "recovery_rate": 0.85},
    "NZL": {"class": "Core", "recovery_rate": 0.82},
    "KOR": {"class": "Core", "recovery_rate": 0.72},
    "ESP": {"class": "Core", "recovery_rate": 0.68},
    "ITA": {"class": "Core", "recovery_rate": 0.65},
    "PRT": {"class": "Core", "recovery_rate": 0.60},
    "GRC": {"class": "Core", "recovery_rate": 0.55},
    "AUT": {"class": "Core", "recovery_rate": 0.80},
    "BEL": {"class": "Core", "recovery_rate": 0.78},
    "SGP": {"class": "Core", "recovery_rate": 0.75},
    "ISR": {"class": "Core", "recovery_rate": 0.72},
    "CZE": {"class": "Core", "recovery_rate": 0.70},
    "SVN": {"class": "Core", "recovery_rate": 0.68},
    "SVK": {"class": "Core", "recovery_rate": 0.65},
    "LTU": {"class": "Core", "recovery_rate": 0.62},
    "LVA": {"class": "Core", "recovery_rate": 0.60},
    "EST": {"class": "Core", "recovery_rate": 0.62},
    "MLT": {"class": "Core", "recovery_rate": 0.68},
    "CYP": {"class": "Core", "recovery_rate": 0.58},
    "ARE": {"class": "Core", "recovery_rate": 0.75},
    "QAT": {"class": "Core", "recovery_rate": 0.78},
    "KWT": {"class": "Core", "recovery_rate": 0.72},
    "BHR": {"class": "Core", "recovery_rate": 0.68},
    "OMN": {"class": "Core", "recovery_rate": 0.68},
    
    # Semi-Periphery
    "CHN": {"class": "Semi", "recovery_rate": 0.55},
    "RUS": {"class": "Semi", "recovery_rate": 0.50},
    "IND": {"class": "Semi", "recovery_rate": 0.48},
    "BRA": {"class": "Semi", "recovery_rate": 0.50},
    "MEX": {"class": "Semi", "recovery_rate": 0.52},
    "TUR": {"class": "Semi", "recovery_rate": 0.42},
    "ZAF": {"class": "Semi", "recovery_rate": 0.45},
    "ARG": {"class": "Semi", "recovery_rate": 0.35},
    "IDN": {"class": "Semi", "recovery_rate": 0.52},
    "SAU": {"class": "Semi", "recovery_rate": 0.58},
    "POL": {"class": "Semi", "recovery_rate": 0.60},
    "HUN": {"class": "Semi", "recovery_rate": 0.55},
    "ROU": {"class": "Semi", "recovery_rate": 0.52},
    "BGR": {"class": "Semi", "recovery_rate": 0.50},
    "HRV": {"class": "Semi", "recovery_rate": 0.52},
    "MNE": {"class": "Semi", "recovery_rate": 0.54},
    "SRB": {"class": "Semi", "recovery_rate": 0.50},
    "ALB": {"class": "Semi", "recovery_rate": 0.48},
    "MKD": {"class": "Semi", "recovery_rate": 0.48},
    "BIH": {"class": "Semi", "recovery_rate": 0.45},
    "GEO": {"class": "Semi", "recovery_rate": 0.50},
    "ARM": {"class": "Semi", "recovery_rate": 0.48},
    "AZE": {"class": "Semi", "recovery_rate": 0.52},
    "KAZ": {"class": "Semi", "recovery_rate": 0.55},
    "UZB": {"class": "Semi", "recovery_rate": 0.50},
    "THA": {"class": "Semi", "recovery_rate": 0.55},
    "MYS": {"class": "Semi", "recovery_rate": 0.58},
    "VNM": {"class": "Semi", "recovery_rate": 0.55},
    "PHL": {"class": "Semi", "recovery_rate": 0.52},
    "UKR": {"class": "Semi", "recovery_rate": 0.35},
    "BLR": {"class": "Semi", "recovery_rate": 0.40},
    
    # Periphery (all others default)
    "default": {"class": "Periphery", "recovery_rate": 0.26}
}

# ─── CONFIG ──────────────────────────────────────────────────────────────

CONFIG = {
    "capital": 100000,
    "max_positions": 6,
    "min_crisis_score": 55,
    "target_return": 0.20,
    "hold_period_seconds": 25,
    "risk_per_trade": 0.15,
    "slippage": 0.10,
    "transaction_costs": 0.08,
    "failure_rate": 0.15,
    "black_swan_rate": 0.05,
    "stagnation_rate": 0.30,
    "partial_recovery_rate": 0.20,
    "max_win": 0.35,
    "max_loss": 0.20,
}

# ─── BOT ENGINE ──────────────────────────────────────────────────────────

class CrisisArbitrageBot:
    def __init__(self, config: Dict):
        self.config = config
        self.capital = config["capital"]
        self.positions = []
        self.trades = []
        self.total_profit = 0
        self.win_count = 0
        self.loss_count = 0
        self.failed_recoveries = 0
        self.black_swan_events = 0
        self.stagnation_events = 0

    def get_country_data(self) -> List[Dict]:
        """Build country data from FSI_2024 and WST classification"""
        countries = []
        for iso, data in FSI_2024.items():
            wst = WST_CLASSIFICATION.get(iso, WST_CLASSIFICATION["default"])
            fsi_score = data["fsi_score"]
            base_score = min(99, max(1, round((fsi_score / 120) * 100)))
            
            class_modifier = 0
            if wst["class"] == "Periphery":
                class_modifier = 5 + 10 / 4
            elif wst["class"] == "Semi":
                class_modifier = 2
            elif wst["class"] == "Core":
                class_modifier = -5
                
            score = min(99, max(1, base_score + class_modifier))
            
            discount = 0.15 + (score / 100) * 0.5
            if wst["class"] == "Periphery":
                discount += 0.10
            elif wst["class"] == "Semi":
                discount += 0.05
            discount = min(0.75, discount)
            
            countries.append({
                "iso": iso,
                "name": data["name"],
                "flag": data["flag"],
                "region": data["region"],
                "score": round(score),
                "fsi_score": fsi_score,
                "fsi_rank": data["rank"],
                "wst_class": wst["class"],
                "recovery_rate": wst["recovery_rate"],
                "discount": discount,
                "momentum": 0
            })
            
        countries.sort(key=lambda x: x["score"], reverse=True)
        return countries

    def score_opportunity(self, country: Dict) -> float:
        """Score a country as a trading opportunity (0-1)"""
        crisis_score = country["score"] / 100
        discount = country["discount"]
        recovery_potential = 1 - country["recovery_rate"]
        structural_bonus = 0.2 if country["wst_class"] == "Periphery" else 0.1 if country["wst_class"] == "Semi" else 0
        
        return min(1, max(0, crisis_score * 0.35 + discount * 0.30 + recovery_potential * 0.20 + structural_bonus * 0.05))

    def calculate_expected_return(self, country: Dict) -> Dict:
        """Calculate expected return for a trade"""
        discount = country["discount"]
        fair_value = 100000
        entry_price = fair_value * (1 - discount)
        slippage_adjusted_entry = entry_price * (1 + self.config["slippage"])
        
        recovery_factor = 1 + (1 - country["recovery_rate"]) * 0.6
        structural_factor = 1.2 if country["wst_class"] == "Periphery" else 1.1 if country["wst_class"] == "Semi" else 0.9
        
        expected_exit_price = fair_value * (0.6 + country["recovery_rate"] * 0.6) * recovery_factor * structural_factor
        slippage_adjusted_exit = expected_exit_price * (1 - self.config["slippage"] * 0.5)
        cost_factor = 1 - self.config["transaction_costs"]
        
        gross_return = (slippage_adjusted_exit - slippage_adjusted_entry) / slippage_adjusted_entry
        net_return = gross_return * cost_factor
        
        return {"entry_price": slippage_adjusted_entry, "exit_price": slippage_adjusted_exit, "net_return": net_return}

    def calculate_realistic_exit_price(self, trade: Dict) -> Dict:
        """Calculate realistic exit price with failure scenarios"""
        fair_value = 100000
        recovery_rate = trade["recovery_rate"]
        entry_price = trade["entry_price"]
        
        # Execution Failure (10%)
        if random.random() < 0.10:
            penalty = 0.85 + random.random() * 0.15
            base_exit = fair_value * (0.6 + recovery_rate * 0.4) * penalty
            exit_price = base_exit * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": exit_price > entry_price}
        
        # Timing Error (15%)
        if random.random() < 0.15:
            timing_penalty = 0.7 + random.random() * 0.2
            base_exit = fair_value * (0.6 + recovery_rate * 0.6) * timing_penalty
            exit_price = base_exit * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": exit_price > entry_price}
        
        # Stagnation (30%)
        if random.random() < self.config["stagnation_rate"]:
            self.stagnation_events += 1
            base_exit = fair_value * (0.6 + random.random() * 0.2)
            exit_price = base_exit * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": exit_price > entry_price}
        
        # Partial Recovery (20%)
        if random.random() < self.config["partial_recovery_rate"]:
            base_exit = fair_value * (0.5 + recovery_rate * 0.3)
            exit_price = base_exit * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": exit_price > entry_price}
        
        # Failed Recovery (15%)
        if random.random() < self.config["failure_rate"]:
            self.failed_recoveries += 1
            base_exit = fair_value * (0.2 + random.random() * 0.2)
            exit_price = base_exit * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": False}
        
        # Black Swan (5%)
        if random.random() < self.config["black_swan_rate"]:
            self.black_swan_events += 1
            crash_factor = 0.1 + random.random() * 0.2
            exit_price = fair_value * crash_factor * (1 - self.config["slippage"] * 0.5) * (1 - self.config["transaction_costs"])
            return {"exit_price": exit_price, "success": False}
        
        # Normal Recovery
        recovery_var = 0.30
        base_recovery = 0.6 + recovery_rate * 0.6
        recovery_factor = 1 + (1 - recovery_rate) * 0.6
        structural_factor = 1.2 if trade["wst_class"] == "Periphery" else 1.1 if trade["wst_class"] == "Semi" else 0.9
        
        variance_noise = 1 + (random.random() - 0.5) * recovery_var
        raw_exit_price = fair_value * base_recovery * recovery_factor * structural_factor * variance_noise
        slippage_adjusted = raw_exit_price * (1 - self.config["slippage"] * 0.5)
        cost_factor = 1 - self.config["transaction_costs"]
        final_exit_price = slippage_adjusted * cost_factor
        
        raw_return = (final_exit_price - entry_price) / entry_price
        capped_return = max(-self.config["max_loss"], min(self.config["max_win"], raw_return))
        
        return {"exit_price": entry_price * (1 + capped_return), "success": capped_return > 0}

    def execute_trade(self, country: Dict):
        """Execute a single trade"""
        if len(self.positions) >= self.config["max_positions"]:
            return
        
        expected = self.calculate_expected_return(country)
        if expected["net_return"] < self.config["target_return"]:
            return
        
        position_size = self.capital * self.config["risk_per_trade"]
        if position_size > self.capital:
            return
        
        trade = {
            "id": time.time() + random.random(),
            "country": country["iso"],
            "country_name": country["name"],
            "flag": country["flag"],
            "entry_price": expected["entry_price"],
            "position_size": position_size,
            "discount": country["discount"],
            "entry_score": country["score"],
            "entry_time": time.time(),
            "is_open": True,
            "recovery_rate": country["recovery_rate"],
            "wst_class": country["wst_class"],
        }
        
        self.positions.append(trade)
        self.capital -= position_size
        print(f"🟢 BUY {trade['flag']} {trade['country_name']} @ ${trade['entry_price']:.0f} ({trade['discount']*100:.0f}% discount, score: {trade['entry_score']})")
        
        # Simulate hold period
        hold_seconds = random.randint(20, 30)
        time.sleep(hold_seconds)
        self.exit_trade(trade["id"])

    def exit_trade(self, trade_id: float):
        """Exit a trade"""
        trade = next((t for t in self.positions if t["id"] == trade_id), None)
        if not trade or not trade["is_open"]:
            return
        
        exit_result = self.calculate_realistic_exit_price(trade)
        trade["exit_price"] = exit_result["exit_price"]
        trade["is_open"] = False
        
        pct = (trade["exit_price"] - trade["entry_price"]) / trade["entry_price"]
        trade["profit"] = trade["position_size"] * pct
        
        self.capital += trade["position_size"] * (1 + pct)
        self.total_profit += trade["profit"]
        self.trades.append(trade)
        
        if pct > 0:
            self.win_count += 1
            print(f"🟢 SELL {trade['flag']} {trade['country_name']} @ ${trade['exit_price']:.0f} ({pct*100:.1f}% profit)")
        else:
            self.loss_count += 1
            print(f"🔴 SELL {trade['flag']} {trade['country_name']} @ ${trade['exit_price']:.0f} ({pct*100:.1f}% loss)")
        
        self.positions.remove(trade)

    def run_cycle(self):
        """Run one trading cycle"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting cycle - Capital: ${self.capital:,.0f}")
        print(f"{'='*60}")
        
        countries = self.get_country_data()
        opportunities = []
        for country in countries:
            score = self.score_opportunity(country)
            if score > 0.25 and country["score"] > self.config["min_crisis_score"]:
                opportunities.append({**country, "opportunity_score": score})
        
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
        print(f"📊 Found {len(opportunities)} viable opportunities")
        
        for country in opportunities[:self.config["max_positions"]]:
            expected = self.calculate_expected_return(country)
            if expected["net_return"] >= self.config["target_return"]:
                self.execute_trade(country)

    def run(self, cycles: int = 1):
        """Run the bot for multiple cycles"""
        print("\n" + "="*60)
        print("🤖 CRISIS ARBITRAGE BOT - v1.0")
        print("="*60)
        print(f"📊 Capital: ${self.config['capital']:,.0f}")
        print(f"💸 Costs: {self.config['transaction_costs']*100:.0f}% fees, {self.config['slippage']*100:.0f}% slippage")
        print("="*60)
        
        for cycle in range(cycles):
            self.run_cycle()
        
        self.print_summary()

    def print_summary(self):
        """Print trading summary"""
        total = len(self.trades)
        win_rate = (self.win_count / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("🏆 TRADING SUMMARY")
        print("="*60)
        print(f"💰 Final P&L: ${self.total_profit:,.2f}")
        print(f"📊 Trades: {total}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"📈 ROI: {(self.total_profit / self.config['capital']) * 100:.1f}%")
        print(f"💵 Cash: ${self.capital:,.0f}")
        print(f"💎 Equity: ${self.capital + self.total_profit:,.0f}")
        print(f"✅ Wins: {self.win_count}")
        print(f"❌ Losses: {self.loss_count}")
        print(f"⚡ Failed Recoveries: {self.failed_recoveries}")
        print(f"💀 Black Swan Events: {self.black_swan_events}")
        print("="*60)

# ─── MAIN ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot = CrisisArbitrageBot(CONFIG)
    bot.run(cycles=1)
