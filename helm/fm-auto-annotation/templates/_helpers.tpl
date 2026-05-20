{{- define "fm.fullname" -}}
{{- printf "annotation-%s" .name -}}
{{- end -}}

{{- define "fm.image" -}}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .image .tag -}}
{{- end -}}
