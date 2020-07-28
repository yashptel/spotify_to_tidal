import tidalapi

tidalapi_parse_album = tidalapi._parse_album


def patch():
    tidalapi._parse_album = _parse_album
    tidalapi.models.Album.picture = picture


def _parse_album(json_obj, artist=None, artists=None):
    obj = tidalapi_parse_album(json_obj, artist, artists)
    image_id = ""
    if json_obj.get("cover"):
        image_id = json_obj.get("cover")

    obj.__dict__.update(image_id=image_id)
    return obj


def picture(obj, width, height):
    return "https://resources.tidal.com/images/{image_id}/{width}x{height}.jpg".format(
        image_id=obj.image_id.replace("-", "/"), width=width, height=height
    )
