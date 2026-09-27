{{- define "oran-sc-chartmuseum.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oran-sc-chartmuseum.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oran-sc-chartmuseum.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "oran-sc-chartmuseum.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "oran-sc-chartmuseum.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "oran-sc-chartmuseum.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Chart.Name -}}
{{- else -}}
default
{{- end -}}
{{- end -}}
