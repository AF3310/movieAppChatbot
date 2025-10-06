def handler(request):
    name = request.query.get("name", "world")
    return {
        "statusCode": 200,
        "body": f"Hello, {name}!"
    }

