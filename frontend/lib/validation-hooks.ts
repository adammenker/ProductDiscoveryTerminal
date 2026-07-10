"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  OutcomeInput,
  PipelineRunInput,
  ProductCreateInput,
  SnapshotInput,
  SupplierQuoteInput
} from "@/types/api";

export const validationKeys = {
  products: ["products"] as const,
  opportunities: ["opportunities"] as const,
  product: (id: string) => ["product", id] as const,
  validation: (id: string) => ["product-validation", id] as const,
  quotes: (id: string) => ["supplier-quotes", id] as const,
  paperTrades: ["paper-trades"] as const,
  backtestSummary: ["backtest-summary"] as const
};

export function useValidateProduct(productId: string) {
  return useQuery({
    queryKey: validationKeys.validation(productId),
    queryFn: () => api.productValidation(productId),
    enabled: Boolean(productId)
  });
}

export function useProductDetail(productId: string) {
  return useQuery({
    queryKey: validationKeys.product(productId),
    queryFn: () => api.product(productId),
    enabled: Boolean(productId)
  });
}

export function useComparableAsins(productId: string) {
  const query = useProductDetail(productId);
  return { ...query, data: query.data?.comparable_asins };
}

export function useSupplierQuotes(productId: string) {
  return useQuery({
    queryKey: validationKeys.quotes(productId),
    queryFn: () => api.supplierQuotes(productId),
    enabled: Boolean(productId)
  });
}

export function useCostCeiling(productId: string) {
  const query = useValidateProduct(productId);
  return { ...query, data: query.data?.economics_validator };
}

export function useConstraintEvaluation(productId: string) {
  const query = useValidateProduct(productId);
  return { ...query, data: query.data?.constraint_evaluation };
}

export function useEvidenceMatrix(productId: string) {
  const query = useValidateProduct(productId);
  return { ...query, data: query.data?.evidence_matrix };
}

export function useDiscoverySources(productId: string) {
  const query = useProductDetail(productId);
  return { ...query, data: query.data?.discovery_source };
}

export function useCreateProduct() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: ProductCreateInput) => api.createProduct(input),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: validationKeys.products });
    }
  });
}

export function useCreateSupplierQuote(productId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: SupplierQuoteInput) => api.createSupplierQuote(productId, input),
    onSuccess: async () => {
      await invalidateProduct(client, productId);
      await client.invalidateQueries({ queryKey: validationKeys.quotes(productId) });
    }
  });
}

export function useEvaluateConstraints(productId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.evaluateConstraints(productId),
    onSuccess: async () => invalidateProduct(client, productId)
  });
}

export function useCreateSnapshot(productId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: SnapshotInput) => api.createSnapshot(productId, input),
    onSuccess: async () => {
      await invalidateProduct(client, productId);
      await client.invalidateQueries({ queryKey: validationKeys.paperTrades });
      await client.invalidateQueries({ queryKey: validationKeys.backtestSummary });
    }
  });
}

export function usePaperTrades() {
  return useQuery({
    queryKey: validationKeys.paperTrades,
    queryFn: api.paperTrades
  });
}

export function useBacktestSummary() {
  return useQuery({
    queryKey: validationKeys.backtestSummary,
    queryFn: api.backtestSummary
  });
}

export function useAddPaperTradeOutcome() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: OutcomeInput }) =>
      api.addPaperTradeOutcome(id, input),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: validationKeys.paperTrades });
      await client.invalidateQueries({ queryKey: validationKeys.backtestSummary });
    }
  });
}

export function useRunResearch(productId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: PipelineRunInput) => api.runPipeline(input),
    onSuccess: async () => {
      await invalidateProduct(client, productId);
      await client.invalidateQueries({ queryKey: ["plugin-runs"] });
    }
  });
}

async function invalidateProduct(
  client: ReturnType<typeof useQueryClient>,
  productId: string
) {
  await Promise.all([
    client.invalidateQueries({ queryKey: validationKeys.product(productId) }),
    client.invalidateQueries({ queryKey: validationKeys.validation(productId) }),
    client.invalidateQueries({ queryKey: validationKeys.products }),
    client.invalidateQueries({ queryKey: validationKeys.opportunities })
  ]);
}
