from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from .forms import ChoiceFileForm
from .forms import UploadFileForm
from .forms import SelectFileForm
from .forms import NumberClusterForm
from .models import UploadFile
from .models import ClusterData
from ml.hotspot_predictor import HotspotPredictor
from ml.hotspot_viewer import HotspotViewer
from joblib import load


@login_required
def index(request):
    form = ChoiceFileForm()
    return render(request, 'ml/index.html', {'form': form})


@login_required
def upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Arquivo enviado com sucesso', extra_tags='success')
            return HttpResponseRedirect(reverse('ml:index'))
    else:
        form = UploadFileForm()
    return render(request, 'ml/upload.html', {'form': form})


@login_required
def configure(request):
    if request.method == 'POST':
        pks = request.POST.getlist('pk')
        if pks:
            context = {
                'select_form': SelectFileForm(pks),
                'n_clusters_form': NumberClusterForm(),
                'range': range(len(pks))
            }
            return render(request, 'ml/configure.html', context)
    return HttpResponseRedirect(reverse('ml:index'))


@login_required
def delete(request):
    if request.method == 'POST':
        pks = request.POST.getlist('pk')
        if pks:
            files = UploadFile.objects.filter(id__in=pks)
            for file in files:
                file.file.delete(save=True)
                file.delete()
    return HttpResponseRedirect(reverse('ml:index'))


@login_required
def train(request):
    if request.method == 'POST':
        filepaths = request.POST.getlist('filepath')
        n_clusters_form = NumberClusterForm(request.POST)
        if filepaths and n_clusters_form.is_valid():
            n_clusters = n_clusters_form.cleaned_data['n_clusters']
            predictor = HotspotPredictor(filepaths=filepaths, n_clusters=n_clusters)
            predictor.save_kmeans_to(settings.MEDIA_ROOT + '/kmeans.joblib')
            clusters_data = predictor.get_results()
            save_results(clusters_data)
            HotspotViewer(clusters_data=clusters_data).save_map_to(settings.MEDIA_ROOT + '/folium.html')
            messages.success(request, 'Treinamento concluído com sucesso', extra_tags='success')
            return HttpResponseRedirect(reverse('ml:index'))
    return HttpResponseRedirect(reverse('index:index'))


def save_results(clusters_data):
    objs = [ClusterData(data=data) for data in clusters_data]
    ClusterData.objects.all().delete()
    ClusterData.objects.bulk_create(objs)


def api(request):
    latitude = request.GET.get('latitude', None)
    longitude = request.GET.get('longitude', None)
    if latitude and longitude:
        try:
            kmeans = load(settings.MEDIA_ROOT + '/kmeans.joblib')
            cluster = kmeans.predict([[latitude, longitude]])
            obj = ClusterData.objects.filter(data__cluster=int(cluster[0]))
            if obj:
                return JsonResponse(obj[0].data)
            else:
                messages.warning(request, 'Objeto não encontrado no Banco de Dados', extra_tags='warning')
        except FileNotFoundError:
            return HttpResponseNotFound('Arquivo não encontrado')
    return HttpResponseRedirect(reverse('index:index'))


def view(request):
    try:
        with open(settings.MEDIA_ROOT + '/folium.html', 'r') as f:
            folium_map = f.read()
            return render(request, 'ml/view.html', {'map': folium_map})
    except FileNotFoundError:
        messages.warning(request, 'Arquivo não encontrado', extra_tags='warning')
        return HttpResponseRedirect(reverse('index:index'))
