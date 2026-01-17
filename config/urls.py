from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/profiling/', include('profiling.urls')),
    path('api/v1/cases/', include('clinical_cases.urls')),
    path('api/v1/simulation/', include('simulation.urls')),
]