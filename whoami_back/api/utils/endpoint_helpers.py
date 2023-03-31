from fastapi import HTTPException, status


def deprecated_endpoint(message: str = "Endpoint deprecated"):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": message,
        },
    )
