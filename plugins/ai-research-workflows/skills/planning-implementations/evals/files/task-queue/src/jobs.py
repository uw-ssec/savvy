"""Jobs the API enqueues."""
from src.tasks.queue import register


@register("resize_image")
def resize_image(path, width):
    return (path, width)


@register("send_digest")
def send_digest(user_id):
    return user_id
