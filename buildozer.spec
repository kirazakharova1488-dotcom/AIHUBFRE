[app]
title = AI HUB Mobile
package.name = aihubmobile
package.domain = org.aihub
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,gguf
version = 0.1.0

# Зависимости приложения
requirements = python3,flet,llama-cpp-python,numpy

orientation = portrait
fullscreen = 1

# Android специфичные настройки
android.archs = arm64-v8a
android.allow_backup = False
android.api = 33
android.minapi = 21
android.ndk_api = 21

# Запрашиваем доступ к памяти, чтобы читать веса моделей с телефона
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
