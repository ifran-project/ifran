{{- define "free5gc-mongodb.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "free5gc-mongodb.fullname" -}}
{{- .Release.Name -}}-{{- .Chart.Name -}}
{{- end -}}

{{- define "free5gc-mongodb.labels" -}}
app.kubernetes.io/name: {{ include "free5gc-mongodb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
