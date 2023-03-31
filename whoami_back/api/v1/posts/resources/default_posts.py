from copy import deepcopy

from whoami_back.api.v1.posts.models import SourceSocialMedia

youtube_post_data = {
    "source": SourceSocialMedia("youtube"),
    "content_uri": "https://www.youtube.com/watch?v=anoV8E4ZZD8",
    "thumbnail_image_uri": "https://whoami-post-images.s3.us-east-2.amazonaws.com/default-post-images/youtube-post.jpg",
    "title": "Chill-out music",
    "meta_title": "[playlist] 내추럴 와인, 음악 그리고 시시콜콜한 이야기",
    "meta_description": """
Photo : Motif 1 , Korea (2021)
Camera : Fuji x100f

☑️ 이 채널에 쓰이는 사진은 모두 제가 직접 촬영했습니다.
☑️ 음악에 대한 저작권 소유자가 아니므로 영상 및 광고를 통해 수익 창출을 할 수 없습니다.
☑️ 유튜브 알고리즘에 의해 자동으로 광고가 발생 될 수 있으며, 광고로 인한 수익은 저작권자에게 돌아갑니다.

📍Contact & SNS : https://linktr.ee/leeplay

☑️ All the photos that I used for this channel were taken by myself  ☺️
☑️ I personally do not make any profit from this channel
☑️ According to Youtube copyright policy, All ads are determined by copyrights holder.
    """,
    "x": 16,
    "y": 140,
    "width": 311,
    "height": 175,
    "scale": 1.0,
}
whoami_post_data = {
    "source": SourceSocialMedia("whoami"),
    "content_uri": "https://whoami-post-images.s3.us-east-2.amazonaws.com/default-post-images/whoami-image-post.jpg",
    "thumbnail_image_uri": "https://whoami-post-images.s3.us-east-2.amazonaws.com/default-post-images/whoami-image-post.jpg",
    "title": "Welcome to whoami",
    "description": "Decorate your board with things that represent you the best and show others who you are.",
    "x": 983,
    "y": 140,
    "width": 320,
    "height": 400,
    "scale": 1.0,
}
web_page_post_data = {
    "source": SourceSocialMedia("unknown"),
    "content_uri": "https://www.16personalities.com/entj-personality",
    "thumbnail_image_uri": "https://whoami-post-images.s3.us-east-2.amazonaws.com/default-post-images/web-page-post.jpeg",
    "title": "MBTI - ENTJ",
    "meta_title": "ENTJ Personality",
    "meta_description": "Commander Personality",
    "x": 356,
    "y": 140,
    "width": 585,
    "height": 175,
    "scale": 1.0,
}


def get_default_posts():
    return [
        deepcopy(youtube_post_data),
        deepcopy(whoami_post_data),
        deepcopy(web_page_post_data),
    ]
