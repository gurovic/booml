from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ...services.runtime import run_code
from ..serializers import CellRunSerializer
from .sessions import ensure_notebook_access


class RunCellView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CellRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cell = serializer.cell
        assert cell is not None

        ensure_notebook_access(request.user, cell.notebook)

        session_id = serializer.validated_data["session_id"]
        result = run_code(session_id, cell.content or "")

        return Response(
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "variables": result.variables,
            },
            status=status.HTTP_200_OK,
        )
