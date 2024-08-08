"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from translator import views as translator_views

urlpatterns = [
    url(r'^$', translator_views.landing, name='landing'),
    url(r'^simulator_home$', translator_views.home, name='home'),
    url(r'^demo/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<play_speed>[\w-]+)/$', translator_views.demo, name='demo'),
    url(r'^replay/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/$', translator_views.replay, name='replay'),
    url(r'^replay_persona_state/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<persona_name>[\w-]+)/$', translator_views.replay_persona_state, name='replay_persona_state'),
    url(r'^process_environment/$', translator_views.process_environment, name='process_environment'),
    url(r'^set_time_value/$', translator_views.set_time_value, name='set_time_value'),
    url(r'^get_time_value/$', translator_views.get_time_value, name='get_time_value'),
    url(r'^input_traits/', translator_views.input_traits, name="input_traits"),
    url(r'^update_environment/$', translator_views.update_environment, name='update_environment'),
    url(r'^path_tester/$', translator_views.path_tester, name='path_tester'),
    url(r'^path_tester_update/$', translator_views.path_tester_update, name='path_tester_update'),
    url(r'^agent_detail/(?P<sim_code>[\w-]+)/$', translator_views.agent_detail, name='agent_detail'),
    url(r'^start_simulation/$', translator_views.start_simulation_view, name='start_simulation'),



    path('admin/', admin.site.urls),
    path('agent_detail/<str:sim_code>/', translator_views.agent_detail, name='agent_detail'),
    path('agent_detail_data/<str:persona_underscore>/<int:step>/<str:sim_code>/', translator_views.agent_detail_data, name='agent_detail_data'),
    path('start-simulation/', translator_views.start_simulation_view, name='start_simulation'),
    path('get-progress/', translator_views.get_progress_view, name='get_progress'),
    path('finish-simulation/', translator_views.finish_simulation_view, name='finish_simulation'),
]