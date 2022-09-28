from typing import List, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, status, Response
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import DoesNotExist

from chapter6.tortoise_relationship.models import (
    PostCreate,
    PostDB,
    PostPartialUpdate,
    PostPublic,
    PostTortoise,
    CommentDB,
    CommentBase,
    CommentTortoise,
)

app = FastAPI()


#### Dependencies ####

async def pagination(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=0),
) -> Tuple[int, int]:
    capped_limit = min(100, limit)
    return (skip, capped_limit)


async def get_post_or_404(id: int) -> PostTortoise:
    try:
        return await PostTortoise.get(id=id).prefetch_related("comments")
    except DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


#### Endpoints ####

@app.get("/posts")
async def list_posts(pagination: Tuple[int, int] = Depends(pagination)) -> List[PostPublic]:
    skip, limit = pagination
    posts = await PostTortoise.all().prefetch_related("comments").offset(skip).limit(limit)
    return [PostPublic.from_orm(post) for post in posts]


@app.get("/posts/{id}", response_model=PostPublic)
async def get_post(post: PostTortoise = Depends(get_post_or_404)) -> PostPublic:
    return PostPublic.from_orm(post)


@app.post("/posts", response_model=PostDB, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate) -> PostDB:
    post_tortoise = await PostTortoise.create(**post.dict())

    return PostDB.from_orm(post_tortoise) # Recall from_orm = True


@app.patch("/posts/{id}", response_model=PostDB)
async def update_post(
    post_update: PostPartialUpdate,
    post: PostTortoise=Depends(get_post_or_404)
) -> PostDB:

    post.update_from_dict(post_update.dict(exclude_unset=True))
    await post.save()
    return PostDB.from_orm(post)


@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post: PostTortoise=Depends(get_post_or_404)):
    await post.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/comments", response_model=CommentDB, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentBase) -> CommentDB:
    
    # First check if post exists
    try:
        await PostTortoise.get(id=comment.post_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Post {id} does not exist"
        )
        
    # Create comment
    comment_tortoise = await CommentTortoise.create(**comment.dict())
    return CommentDB.from_orm(comment_tortoise)


#### ORM config ####

TORTOISE_ORM = {
    "connections": {"default": "sqlite://chapter6_tortoise.db"},
    "apps": {
        "models": {
            "models": ["chapter6.tortoise_relationship.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)
