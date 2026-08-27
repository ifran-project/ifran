{{- define "open5gs-mongodb.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "open5gs-mongodb.fullname" -}}
{{- .Release.Name -}}-{{- .Chart.Name -}}
{{- end -}}

{{- define "open5gs-mongodb.labels" -}}
app.kubernetes.io/name: {{ include "open5gs-mongodb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
