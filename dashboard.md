---
title: Yepisyeni Türkiye — OSINT Dashboard
---

# OSINT Gösterge Paneli / Dashboard

Bu sayfa, kamu yararına erişilebilir OSINT izleme platformlarının dizinidir.
Makale akışı değil — araçlar ve veri kaynakları. Türkiye-İsrail arasındaki ticaret inkârının AIS verisiyle çürütülmesi gibi kullanım durumları için gerekli olan enstrümantasyon katmanı.

*This page indexes public-benefit OSINT monitoring platforms — tools and data sources, not an article feed. Instrumentation for factual debunks (e.g. shipping-denial refutations via AIS data).*

**Filtreler / Filters:**

- Kamu erişimine açık, VPN gerektirmez / publicly accessible, no VPN required
- AB yaptırımlı yayıncılar dışlandı / no EU-sanctioned outlets
- Doxxing yok / no individual-targeting platforms
- Yaptırımlı/yasaklı örgütlerle bağlantılı değil / no sanctioned or banned affiliates

Haber akışı / news stream: [`index.md`](index.md). Kaynak denetimi / source audit: [`phase0/PHASE0_REPORT.md`](phase0/PHASE0_REPORT.md).

---

## Denizcilik / Maritime / Shipping

- **[MarineTraffic](https://www.marinetraffic.com)** 🌍 *[Link]*
  Paid API; ToS restricts raw AIS redistribution.
- **[VesselFinder](https://www.vesselfinder.com)** 🌍 *[Link]*
  Paid API.
- **[AIS Hub](https://www.aishub.net)** 🌍 *[API]*
  Community AIS exchange.
- **[Information Fusion Centre — Indian Ocean Region](https://www.ifc-ior.org)** 🌏 *[Link]*
  Indian Navy maritime security reports (piracy, IUU fishing, IOR incidents).
- **[MSCHOA (EU NAVFOR)](https://www.mschoa.org)** 🌍 *[Link]*
  Red Sea / Gulf of Aden incident advisories.

---

## Havacılık / Aviation

- **[ADS-B Exchange](https://www.adsbexchange.com)** 🌍 *[API]*
  Unfiltered ADS-B — does not blocklist military/gov aircraft (key OSINT differentiator).
- **[Flightradar24](https://www.flightradar24.com)** 🌍 *[Link]*
  Paid API.
- **[OpenSky Network](https://opensky-network.org)** 🌍 *[API]*
  Academic ADS-B.

---

## Ticaret ve Emtia / Trade / Commodity

- **[UN Comtrade](https://comtradeplus.un.org)** 🌍 *[API]*
  Bilateral trade flows by commodity (HS code).
- **[Trase](https://trase.earth)** 🌍 *[CSV bulk]*
  Supply-chain mapping for deforestation-risk commodities (soy, beef, palm, cocoa).
- **[Observatory of Economic Complexity](https://oec.world)** 🌍 *[API]*
  Visual bilateral trade built on Comtrade + BACI.

---

## Uydu Verisi / Satellite / Earth Observation

- **[Copernicus Data Space](https://dataspace.copernicus.eu)** 🌍 *[API]*
  ESA Sentinel-1/2/3/5P open archive.
- **[NASA Worldview / EOSDIS](https://worldview.earthdata.nasa.gov)** 🌍 *[API]*
  Near-real-time global imagery (MODIS, VIIRS, Landsat).
- **[Planet Labs — Disaster Data Program](https://www.planet.com/disasterdata/)** 🌍 *[Link]*
  Open-license imagery subset for active disasters/conflicts (CC-BY-SA).
- **[CRESDA (China Centre for Resources Satellite Data)](https://www.cresda.com/CN/)** 🌏 *[Link]* ⚠️ *needs verification / doğrulama gerekiyor*
  Chinese public satellite data (Gaofen, Ziyuan).

---

## Yaptırımlar ve Şirketler / Sanctions / Corporate

- **[OpenSanctions](https://www.opensanctions.org)** 🌍 *[API]*
  Consolidated global sanctions + PEP database.
- **[OpenCorporates](https://opencorporates.com)** 🌍 *[API]*
  Largest open corporate registry aggregator.
- **[OCCRP Aleph](https://aleph.occrp.org)** 🌍 *[Link]*
  Entity search across leaks, registries, sanctions, court records.

---

## Çatışma Verisi / Conflict / Event Data

- **[ACLED](https://acleddata.com)** 🌍 *[API]*
  Armed Conflict Location and Event Data.
- **[GDELT Project](https://www.gdeltproject.org)** 🌍 *[API]*
  Machine-coded global event stream from news media, 15-minute updates.
- **[Uppsala Conflict Data Program](https://ucdp.uu.se)** 🌍 *[API]*
  Longest-running academic conflict dataset.
- **[Airwars](https://airwars.org)** 🌍 *[Link]*
  Civilian-harm tracking across conflicts (Iraq, Syria, Yemen, Gaza, Ukraine).
- **[LiveUAMap](https://liveuamap.com)** 🌍 *[Link]*
  Live conflict event map (Ukraine, MENA, wider war theatres).
- **[Conflict Intelligence Team](https://citeam.org)** 🇪🇺 *[Link]*
  Russian anti-Kremlin OSINT collective (Ruslan Leviev).

---

## Genel Altyapı / General Infrastructure

- **[Submarine Cable Map (TeleGeography)](https://www.submarinecablemap.com)** 🌍 *[JSON bulk]*
  Public cable and landing-station map.
- **[Cloudflare Radar](https://radar.cloudflare.com)** 🌍 *[API]*
  Global internet traffic, BGP, outages, attack trends from CF vantage.
- **[IODA (Internet Outage Detection and Analysis)](https://ioda.inetintel.cc.gatech.edu)** 🌍 *[API]*
  Georgia Tech academic outage detection.
- **[USGS Earthquake Hazards](https://earthquake.usgs.gov)** 🌍 *[Atom]*
  Global real-time earthquake feed.
- **[EMSC (European-Mediterranean Seismological Centre)](https://www.emsc-csem.org)** 🇪🇺 *[RSS]*
  European seismic monitoring.
- **[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov)** 🌍 *[API]*
  Near-real-time active fire detections (MODIS/VIIRS).

---

*30 platform • Son güncelleme / last build: build-time*
