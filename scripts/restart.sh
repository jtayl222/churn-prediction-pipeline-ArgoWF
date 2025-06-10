
echo "Shutting down"

kubectl delete configmap seldon-churn-template -n argowf
kubectl delete seldondeployment churn-xgboost-model -n argowf
kubectl delete secret minio-credentials-wf
argo -n argowf delete churn-pipeline

echo
echo
echo
./scripts/update-configmap.sh
echo
echo
echo

kubectl apply -f k8s/seldon-rbac.yaml
kubectl apply -f k8s/churn-pipeline-scripts-configmap.yaml -o yaml

echo
echo
echo
kubectl create configmap seldon-churn-template --from-file=k8s/seldon-churn-deployment-template.yaml -n argowf
kubectl get configmap seldon-churn-template -n argowf
echo
echo
echo

argo submit -n argowf argowf.yaml
set +x
echo "Next:"
echo ""
echo "# Describe pod:"
echo 'kubectl -n argowf describe $(kubectl -n argowf get pods -l app=churn-xgboost-model-default-0-churn-classifier -o name)'
echo ""
echo "# Get log files from container:"
echo "kubectl -n argowf logs \$(kubectl -n argowf get pods -l app=churn-xgboost-model-default-0-churn-classifier -o name | sed 's/pod\///') -c churn-classifier-model-initializer"
echo ""
echo "# Visit the container:"
echo "kubectl exec -it \$(kubectl -n argowf get pods -l app=churn-xgboost-model-default-0-churn-classifier -o name | sed 's/pod\///') -n argowf -c churn-classifier-model-initializer -- /bin/sh"
echo ""
echo "Get initContainer details:"
echo "kubectl -n argowf get pods -l app=churn-xgboost-model-default-0-churn-classifier -o yaml > pod-detail-out.yaml"
echo "yq '.spec.containers.name' pod-detail-out.yaml"
echo "yq '.spec.initContainers' pod-detail-out.yaml"
echo
echo "POD_NAME=\$(kubectl -n argowf get pods -l app=churn-xgboost-model-default-0-churn-classifier -o jsonpath='{.items[0].metadata.name}')"
echo 'kubectl -n argowf logs $POD_NAME -c churn-classifier -f'

