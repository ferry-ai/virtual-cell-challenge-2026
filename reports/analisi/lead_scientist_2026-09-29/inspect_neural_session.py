"""Read exact version-1 Kaggle status and safe metadata through the installed SDK."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--latest", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest, ApiGetKernelSessionStatusRequest
    api = KaggleApi()
    api.authenticate()
    data = {"observed_utc": datetime.now(timezone.utc).isoformat(),
            "kernel": "davidmaisterx/vcc-lead-neural-sources-r1", "requested_version_label": "latest" if args.latest else "1"}
    with api.build_kaggle_client() as client:
        request = ApiGetKernelSessionStatusRequest()
        request.user_name = "davidmaisterx"
        request.kernel_slug = "vcc-lead-neural-sources-r1"
        if not args.latest:
            request.version_label = "1"
        status = client.kernels.kernels_api_client.get_kernel_session_status(request)
        data["status_response"] = status.to_dict(ignore_defaults=False)
        request = ApiGetKernelRequest()
        request.user_name = "davidmaisterx"
        request.kernel_slug = "vcc-lead-neural-sources-r1"
        if not args.latest:
            request.version_label = "1"
        result = client.kernels.kernels_api_client.get_kernel(request)
        fields = ["id", "ref", "title", "author", "slug", "last_run_time", "language", "kernel_type",
                  "is_private", "enable_gpu", "enable_tpu", "enable_internet", "dataset_data_sources",
                  "current_version_number", "docker_image", "machine_shape"]
        data["metadata"] = {field: getattr(result.metadata, field) for field in fields}
        data["returned_source_sha256"] = hashlib.sha256(result.blob.source.encode()).hexdigest()
    data["limitations"] = "Installed SDK status has only status/failure_message; metadata has last_run_time but no session ID, PID, step or fold progress. No logs stream retry."
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, default=str)
        stream.write("\n")
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
