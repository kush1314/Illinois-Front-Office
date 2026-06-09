"use client";

import dynamic from "next/dynamic";
import type { ComponentType } from "react";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as ComponentType<any>;

export default Plot;
