import { SearchQueryVariables } from "./containers/BaseSearch";

export const APP_MOUNT_URI = "/shop/dashboard/next/";
export const API_URI = "/shop/graphql/";

export const DEFAULT_INITIAL_SEARCH_DATA: SearchQueryVariables = {
  after: null,
  first: 5,
  query: ""
};

export const PAGINATE_BY = 20;
