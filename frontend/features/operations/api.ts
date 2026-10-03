import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    Operation,
} from "./contracts";

export function getOperation(
    operationId: string,
): Promise<Operation> {
    return apiRequest<Operation>(
        `/operations/${operationId}`,
    );
}