# 고정된 610.43.03 펌웨어 입력

`make inputs`는 `fetch_artifacts.py`를 실행해 `artifacts-610.43.03.json`에 지정된 NVIDIA 오픈 커널 모듈 소스 아카이브와 정확한 CachyOS `nvidia-utils` 패키지를 내려받습니다. HTTPS를 사용하며, 캐시에 넣기 전에 SHA-256을 검증합니다. 캐시된 파일도 매번 다시 검사합니다. 내려받은 파일을 실행하거나 설치하지는 않습니다.

그다음 `make firmware`는 커널 모듈이 `gpu-unlock/610.43.03/`에서 읽을 다섯 파일을 생성합니다.

- `generate_v67.py`: 패키지에서 `gsp_ga10x.bin`과 NVIDIA 라이선스를 추출하고, 64,000바이트의 `v67-ga102-610.43.03.bin`을 생성합니다.
- `extract_boot_assets.py`: 소스 아카이브에서 `booter_load_ga102.bin`, `gsp_boot_ga102.bin`, `gsp_boot_desc_ga102.bin`을 생성합니다.

두 스크립트는 출력 파일을 기록하기 전에 모든 입력과 생성 결과를 고정된 SHA-256과 비교합니다. zstd 형식의 tar 아카이브를 처리하려면 Python 3.14 이상이 필요합니다. 출처와 라이선스는 [NOTICE.md](NOTICE.md)를 확인하십시오.

## GA106 실기 검증과의 관계

RTX 3060 12GB GA106 실기 시험에서도 위의 고정된 입력을 사용했습니다. 실제 GPU에서 성공했다는 기록은 저장소 최상위 [README.md](../README.md)에 환경·성능·한계와 함께 정리했습니다.

GA102와 GA106이 공통 로더 자산을 사용한다는 소스 근거만으로 모든 GA106 카드의 호환성이 입증되는 것은 아닙니다. 이번에 검증한 카드 한 장의 결과와 다른 하드웨어에 대한 지원 범위는 구분해야 합니다. NVIDIA 드라이버·펌웨어·CUDA 바이너리를 별도로 배포할 수 있다는 의미도 아닙니다.
