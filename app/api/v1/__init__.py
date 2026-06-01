"""API v1 routes — 每个文件通过 router_v1 注册路由。"""

from app.api.v1.router import router_v1

import app.api.v1.auth  # noqa
import app.api.v1.user  # noqa
import app.api.v1.task  # noqa
import app.api.v1.image  # noqa
import app.api.v1.question  # noqa
import app.api.v1.block  # noqa
import app.api.v1.correction  # noqa
import app.api.v1.knowledge  # noqa
import app.api.v1.question_chunk  # noqa
import app.api.v1.model  # noqa
import app.api.v1.homework  # noqa
import app.api.v1.config  # noqa
