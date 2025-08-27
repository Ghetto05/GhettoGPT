from os import environ

channel_bot_setup = 991787747977220257
channel_bot_tests = 1403793063330975774
channel_secret_archive = 1408349748334825493
channel_moderators = 954746778006216774
channel_github_board = 1395175095630041221
channel_changelog_update = 1395314696772653056
channel_weekly_changelog_update = 1395314867958710322

user_ghetto05 = 714263935746048072

role_moderator = 954741893361713242
role_changelog_update = 1395315680622149642
role_weekly_changelog_update = 1395315806383902730

message_github_board = 1395180150764867758

is_dev = environ.get("ENV") == "dev"

def get_channel(channel_supplier):
    if is_dev:
        return channel_bot_tests
    return channel_supplier