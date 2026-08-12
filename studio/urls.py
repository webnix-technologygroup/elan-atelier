from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.home, name="home"),
    path("services/", views.services, name="services"),
    path("services/<slug:slug>/", views.service_detail, name="service_detail"),
    path("about/", views.about, name="about"),
    path("team/", views.team, name="team"),
    path("team/<slug:slug>/", views.team_detail, name="team_detail"),
    path("gallery/", views.gallery, name="gallery"),
    path("journal/", views.journal, name="journal"),
    path("journal/<slug:slug>/", views.article, name="article"),
    path("contacts/", views.contacts, name="contacts"),
    path("booking/", views.booking, name="booking"),
    path(
        "booking/success/<uuid:public_id>/",
        views.booking_success,
        name="booking_success",
    ),
    path(
        "booking/<uuid:public_id>/calendar.ics", views.booking_ics, name="booking_ics"
    ),
    path("api/available-slots/", views.available_slots, name="available_slots"),
    path("api/masters/", views.available_masters, name="available_masters"),
    path("cabinet/login/", views.login_request, name="login_request"),
    path("cabinet/code/", views.login_code, name="login_code"),
    path("cabinet/magic/<str:token>/", views.magic_login, name="magic_login"),
    path("cabinet/logout/", views.logout_customer, name="logout_customer"),
    path("cabinet/", views.cabinet, name="cabinet"),
    path(
        "cabinet/booking/<uuid:public_id>/", views.booking_detail, name="booking_detail"
    ),
    path(
        "cabinet/booking/<uuid:public_id>/cancel/",
        views.cancel_booking,
        name="cancel_booking",
    ),
    path(
        "cabinet/booking/<uuid:public_id>/reschedule/",
        views.request_reschedule,
        name="request_reschedule",
    ),
    path(
        "cabinet/booking/<uuid:public_id>/reschedule-slots/",
        views.reschedule_slots,
        name="reschedule_slots",
    ),
    path("privacy/", views.privacy, name="privacy"),
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
]
