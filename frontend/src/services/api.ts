import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  // Do not set a global Content-Type here. Axios automatically uses JSON for
  // ordinary objects and multipart/form-data (with the required boundary) for
  // FormData. A forced application/json header makes FastAPI reject uploads
  // with 422 because it cannot parse the required `file` form field.
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export { api };
