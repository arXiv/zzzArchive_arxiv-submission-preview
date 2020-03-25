# Deployment Instructions for submission-preview

To install submission-preview to the development namespace in the kubernetes cluster:

```
helm install ./ --name=submission-preview \
  --set=image.tag=0.1rc1 --tiller-namespace=development \
  --namespace=development --set=vault.enabled=1 \
  --set=vault.host=<VAULT_HOST_IP> --set=vault.port=8200
```

This assumes that the requisite Vault roles and policies have already been installed.

To delete the pod, run:
```
helm del --purge submission-preview --tiller-namespace=development
```

Notes:
- `image.tag`: this refers to the tag in [dockerhub](https://hub.docker.com/repository/docker/arxiv/submission-preview)
- `vault.host`: the actual IP of the Vault host can be retrieved from most of the other pods, for example by running the following command on one of the existing pods, e.g.:
```
$ kubectl describe pod submission-ui-8447fff4b7-cbqc2 | grep VAULT_HOST
```
