import {
    apiRequest,
} from "./client";

import type {
    Operation,
} from "../../types/operation";

export async function getOperation(
    operationId: string,
): Promise<Operation> {
    return apiRequest<Operation>(
        `/api/v3/operations/${operationId}`,
    );
}