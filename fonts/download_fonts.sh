#!/bin/bash

# Noto Sans JP variations
curl -L -o "NotoSansJP-Light.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Light.otf"
curl -L -o "NotoSansJP-Medium.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Medium.otf"
curl -L -o "NotoSansJP-Black.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Black.otf"

# Noto Serif JP
curl -L -o "NotoSerifJP-Regular.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/Japanese/NotoSerifJP-Regular.otf"
curl -L -o "NotoSerifJP-Bold.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/Japanese/NotoSerifJP-Bold.otf"
curl -L -o "NotoSerifJP-Black.ttf" "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/Japanese/NotoSerifJP-Black.otf"

# M+ fonts (popular for video subtitles)
curl -L -o "MPLUSRounded1c-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-Regular.ttf"
curl -L -o "MPLUSRounded1c-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-Bold.ttf"
curl -L -o "MPLUSRounded1c-Black.ttf" "https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-Black.ttf"
curl -L -o "MPLUS1p-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Regular.ttf"
curl -L -o "MPLUS1p-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Bold.ttf"

# Sawarabi Gothic and Mincho
curl -L -o "SawarabiGothic-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/sawarabigothic/SawarabiGothic-Regular.ttf"
curl -L -o "SawarabiMincho-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/sawarabimincho/SawarabiMincho-Regular.ttf"

# Kosugi fonts
curl -L -o "Kosugi-Regular.ttf" "https://github.com/google/fonts/raw/main/apache/kosugi/Kosugi-Regular.ttf"
curl -L -o "KosugiMaru-Regular.ttf" "https://github.com/google/fonts/raw/main/apache/kosugimaru/KosugiMaru-Regular.ttf"

# Zen Kaku Gothic
curl -L -o "ZenKakuGothicNew-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/ZenKakuGothicNew-Regular.ttf"
curl -L -o "ZenKakuGothicNew-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/ZenKakuGothicNew-Bold.ttf"
curl -L -o "ZenKakuGothicNew-Black.ttf" "https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/ZenKakuGothicNew-Black.ttf"

# Zen Maru Gothic
curl -L -o "ZenMaruGothic-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/zenmarugothic/ZenMaruGothic-Regular.ttf"
curl -L -o "ZenMaruGothic-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/zenmarugothic/ZenMaruGothic-Bold.ttf"

echo "Font download complete!"
