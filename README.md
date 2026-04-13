# tistory-jsonld-generator
# 티스토리 JSON-LD 스키마 자동 생성기

티스토리 블로그 포스팅 URL을 입력하면 JSON-LD 스키마 코드를 자동으로 생성해주는 파이썬 도구입니다.
AEO(Answer Engine Optimization)와 GEO(Generative Engine Optimization) 최적화를 위해 제작했습니다.

## 주요 기능

- 티스토리 포스팅 URL 하나만 입력하면 JSON-LD 코드 자동 생성
- 블로그명, 저자, 제목, 발행일, 카테고리, 이미지, 태그 자동 추출
- BlogPosting / NewsArticle / Article / Review 스키마 타입 자동 판별
- 추출된 정보 미리보기 후 수동 수정 가능
- 결과물 txt 파일로 자동 저장
- 어떤 티스토리 블로그든 사용 가능

## 사용 환경

- Python 3.9 이상
- Mac / Windows 모두 지원

## 설치 방법

```bash
pip install requests beautifulsoup4
```

## 실행 방법

```bash
python3 tistory_jsonld.py
```

## 사용 순서

1. 프로그램 실행 후 티스토리 포스팅 URL 입력
2. 자동 추출된 정보 미리보기 확인
3. Enter(그대로 생성) 또는 n(수동 수정) 선택
4. 생성된 JSON-LD 코드 복사
5. 티스토리 HTML 편집 모드 맨 아래에 붙여넣기

## 티스토리 적용 방법

1. 티스토리 포스팅 편집 화면에서 HTML 모드로 전환
2. 생성된 `<script type="application/ld+json">` 코드 전체를 맨 아래에 붙여넣기
3. 저장 또는 발행

## 적용 확인

아래 링크에서 포스팅 URL을 입력하면 스키마 적용 여부를 확인할 수 있습니다.

https://search.google.com/test/rich-results

## 다운로드

| 운영체제 | 파일 |
|---|---|
| Mac | 준비 중 |
| Windows | 준비 중 |

실행파일은 Releases 탭에서 다운로드할 수 있습니다. (업데이트 예정)

## 만든 이

sseoteo — Claude AI와 함께 제작
