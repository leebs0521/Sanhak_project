import datetime
import json

import requests

from django.shortcuts import render, redirect
from django.core.paginator import Paginator

from base.settings.base import OBJECT_STORAGE_URL, MEDIA_ROOT
from labeling.models import AudioFile, STTResult

import os

from labeling.utils import FileClass, save_json_to_model


def home(request):
    page = int(request.GET.get('page', 1))
    work_list = AudioFile.objects.order_by('-start_time')
    paginator = Paginator(work_list, 5)
    page_obj = paginator.get_page(page)
    file_list = get_file_list()
    context = {'work_list': page_obj, 'file_list': file_list}
    return render(request, 'labeling/work_list.html', context)


def edit_file(request, pk):  # edit_file 가는 함수
    file = AudioFile.objects.get(pk=pk)
    url = 'labeling'+file.audio_file.url
    file.status = '작업중'   # 작업 상태 변경
    file.save()
    result = STTResult.objects.get(id=file.id)
    result_list = result.result_file
    context = {'file': file, 'url': url, 'result_list': result_list}
    return render(request, 'labeling/edit_file.html', context)


def return_json(request):
    """edit_file 에서 수정한 값을 textEdited 에 넣어줌 그리고 db 저장"""
    if request.method == 'POST':
        pk = request.POST.get('file_id')
        file = AudioFile.objects.get(pk=pk)  # 파일 작업 상태 변경
        result = STTResult.objects.get(pk=pk)
        json_list = result.result_file
        edited_text = request.POST.getlist('text_edited')
        for jsonList, editedText in zip(json_list, edited_text):
            jsonList['textEdited'] = editedText
            if editedText is None:
                continue
        file.status = '작업완료'  # 파일 작업 상태 변경
        file.end_time = datetime.datetime.now()
        file.save()

        result.result_file = json_list
        result.save()

        return redirect('/labeling/')


def add_file(request):
    """로컬에 있는 오디오 파일을 서버에 업로드 하는 코드"""

    if request.method == 'POST':
        audio = request.FILES['audio_file']
        print(audio)
        language = request.POST['language']
        fileupload = AudioFile(
            audio_file=audio,
            language=language,
            status="작업 대기",
            request_method="파일 업로드",
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
        )

        fileupload.save()
        stt_api(fileupload)
        return redirect('/labeling/')
    else:

        return redirect('/labeling/')


def delete_file(request):
    if request.method == 'GET':
        delete_list = request.GET.getlist('checked')
        for delete_id in delete_list:
            record = AudioFile.objects.get(id=delete_id)
            record.delete()

        return redirect('/labeling/')


def search_result(request):
    """특정 파일 검색"""

    if request.method == 'POST':
        query = request.POST.get('search_text')
        work_list = AudioFile.objects.filter(audio_file__contains=query)
        context = {'work_list': work_list}
        return render(request, 'labeling/work_list.html', context)


def get_file_list():
    path = MEDIA_ROOT + OBJECT_STORAGE_URL
    file_list = os.listdir(path)

    file_class_list = []

    for file_name in file_list:
        file = FileClass(file_name)
        file_class_list.append(file)

    return file_class_list


def add_object_storage(request):
    if request.method == "GET":
        file_name = request.GET.get('file')
        language = request.GET.get('language')

        fileupload = AudioFile(
            language=language,
            status="작업 대기",
            request_method="Object Storage에서 선택",
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
        )
        fileupload.audio_file.name = 'testob/' + file_name
        fileupload.save()
        stt_api(fileupload)
        return redirect('/labeling/')


def stt_api(file):
    """file -> STT 모델에 전달"""
    """result file -> JSON"""

    model_url = "https://bigdataws.wehago.com/model_api/stt/asr"
    audio = file.audio_file.file

    body_context = {'audio': audio}

    response = requests.post(model_url, files=body_context)

    if response.status_code == 200:
        result_json = response.json()
        result = save_json_to_model(result_json, file)

    else:
        pass


def test(request):
    audio = AudioFile.objects.get(id=2)
    result = STTResult.objects.get(id=audio.id)
    result_list = result.result_file
    print(result_list)
    print(type(result_list))
    context = {"audio": audio, 'result_list': result_list}
    return render(request, 'labeling/test.html', context)
