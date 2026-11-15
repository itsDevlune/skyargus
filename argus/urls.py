from django.urls import path

from apps.core import cube_views
from apps.core import views as v
from apps.core.exports import report_export

urlpatterns = [
    path('api/v1/cubes', cube_views.load_cube),
    path('api/v1/cubes/<uuid:pk>/planes/<int:index>', cube_views.plane),
    path('api/v1/cubes/<uuid:pk>/spectrum', cube_views.spectrum),
    path("api/v1/analyses", v.analyses),
    path("reports/<uuid:pk>", v.report_page),
    path("api/v1/reports/<uuid:pk>/exports/<str:format>", report_export),
    path("", v.explorer),
    path("sources/", v.sources),
    path("api/v1/resolve", v.resolution),
    path("api/v1/searches", v.searches),
    path("api/v1/hips/cube", v.hips_cube),
    path("api/v1/jobs/<uuid:pk>", v.jobs),
    path("api/v1/sequences/<uuid:pk>", v.sequences),
    path("api/v1/artifacts/<uuid:pk>", v.artifacts),
    path("api/v1/catalogs/gaia", v.catalogs),
    path("api/v1/catalogs/wise", v.wise_catalog),
    path("api/v1/candidates", v.candidates),
    path("api/v1/candidates/<uuid:pk>", v.candidates),
    path("api/v1/reports", v.reports),
    path("api/v1/reports/<uuid:pk>", v.report),
    path("api/v1/reports/<uuid:pk>/shares", v.shares),
    path("api/v1/reports/<uuid:pk>/reviews", v.reviews),
    path("shared/<str:token>", v.shared),
    path("embed/<str:token>", v.shared),
    path("health/", v.health),
]
