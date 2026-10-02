#!/usr/bin/env bash
# Download the Quran and hadith datasets (not stored in the repo because of size).
set -e
cd "$(dirname "$0")/data"

if [ ! -d hadith-api ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/fawazahmed0/hadith-api.git
  (cd hadith-api && git sparse-checkout set --no-cone '/info.min.json' \
    $(for b in bukhari muslim abudawud tirmidhi nasai ibnmajah malik nawawi qudsi; do
        echo "/editions/ara-$b.min.json /editions/eng-$b.min.json"; done))
fi

if [ ! -d quran-api ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/fawazahmed0/quran-api.git
  (cd quran-api && git sparse-checkout set --no-cone '/info.min.json' '/editions.min.json' \
    '/editions/ara-quransimple.min.json' '/editions/ara-quranuthmanihaf.min.json' \
    $(for t in ummmuhammad abdullahyusufal mohammedmarmadu muhammadtaqiudd; do echo "/editions/eng-$t.min.json"; done))
fi

cd ../backend && python3 build_index.py
