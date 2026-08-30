{{- define "oran-sc-xapp-onboarder.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oran-sc-xapp-onboarder.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oran-sc-xapp-onboarder.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "oran-sc-xapp-onboarder.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "oran-sc-xapp-onboarder.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "oran-sc-xapp-onboarder.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Chart.Name -}}
{{- else -}}
default
{{- end -}}
{{- end -}}
