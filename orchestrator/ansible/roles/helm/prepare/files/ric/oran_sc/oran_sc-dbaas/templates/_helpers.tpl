{{- define "oran-sc-dbaas.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oran-sc-dbaas.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oran-sc-dbaas.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "oran-sc-dbaas.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "oran-sc-dbaas.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "oran-sc-dbaas.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Chart.Name -}}
{{- else -}}
default
{{- end -}}
{{- end -}}
