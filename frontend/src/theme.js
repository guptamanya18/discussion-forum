import { createTheme, alpha } from "@mui/material/styles";

const getTheme = (mode) => {
  const isDark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: { main: "#FF4500", light: "#FF6D33", dark: "#CC3700" },
      secondary: { main: isDark ? "#818384" : "#555658", light: "#9A9B9D", dark: "#636466" },
      background: {
        default: isDark ? "#0B1416" : "#DAE0E6",
        paper: isDark ? "#131F22" : "#FFFFFF",
      },
      text: {
        primary: isDark ? "#D7DADC" : "#1C1C1C",
        secondary: isDark ? "#818384" : "#787C7E",
      },
      error: { main: "#FF5252" },
      success: { main: isDark ? "#69F0AE" : "#46D160" },
      warning: { main: "#FFD740" },
      divider: isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.1)",
      action: {
        hover: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)",
        selected: isDark ? "rgba(255,69,0,0.16)" : "rgba(255,69,0,0.08)",
      },
    },
    typography: {
      fontFamily: "\"IBM Plex Sans\", \"Inter\", \"Roboto\", \"Helvetica\", \"Arial\", sans-serif",
      h4: { fontWeight: 700, letterSpacing: "-0.02em" },
      h5: { fontWeight: 600, letterSpacing: "-0.01em" },
      h6: { fontWeight: 600 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isDark ? "#0B1416" : "#DAE0E6",
            minHeight: "100vh",
          },
          scrollbarWidth: "thin",
          scrollbarColor: `${isDark ? "#333" : "#bbb"} ${isDark ? "#0B1416" : "#DAE0E6"}`,
          "::-webkit-scrollbar": { width: "8px" },
          "::-webkit-scrollbar-track": { background: isDark ? "#0B1416" : "#DAE0E6" },
          "::-webkit-scrollbar-thumb": { background: isDark ? "#333" : "#bbb", borderRadius: "4px" },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            border: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.1)"}`,
            transition: "border-color 0.2s, box-shadow 0.2s",
            "&:hover": {
              borderColor: isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.2)",
              boxShadow: isDark ? "0 2px 8px rgba(0,0,0,0.3)" : "0 2px 8px rgba(0,0,0,0.06)",
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          contained: {
            boxShadow: "none",
            "&:hover": { boxShadow: "0 2px 8px rgba(255,69,0,0.35)" },
          },
          outlined: {
            borderColor: isDark ? "rgba(255,69,0,0.5)" : "rgba(255,69,0,0.3)",
            "&:hover": {
              borderColor: "#FF4500",
              backgroundColor: alpha("#FF4500", 0.08),
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500 },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              "& fieldset": { borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.15)" },
              "&:hover fieldset": { borderColor: "rgba(255,69,0,0.5)" },
            },
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            backgroundColor: isDark ? "#131F22" : "#FFFFFF",
            borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.1)"}`,
            boxShadow: isDark ? "0 1px 3px rgba(0,0,0,0.4)" : "0 1px 3px rgba(0,0,0,0.06)",
            color: isDark ? "#D7DADC" : "#1C1C1C",
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            backgroundImage: "none",
            border: `1px solid ${isDark ? "rgba(124,77,255,0.2)" : "rgba(0,0,0,0.1)"}`,
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            border: `1px solid ${isDark ? "rgba(255,255,255,0.065)" : "rgba(0,0,0,0.1)"}`,
          },
        },
      },
      MuiTableHead: {
        styleOverrides: {
          root: {
            "& .MuiTableCell-head": {
              backgroundColor: isDark ? "#272729" : "#F6F7F8",
              fontWeight: 700,
              color: isDark ? "#B388FF" : "#651FFF",
            },
          },
        },
      },
      MuiListItem: {
        styleOverrides: { root: { borderRadius: 8 } },
      },
      MuiAlert: {
        styleOverrides: { root: { borderRadius: 8 } },
      },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: "none" } },
      },
      MuiBadge: {
        styleOverrides: {
          colorError: { background: "linear-gradient(135deg, #FF5252 0%, #FF1744 100%)" },
        },
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            backgroundImage: "none",
            border: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.1)"}`,
            boxShadow: isDark ? "0 4px 20px rgba(0,0,0,0.5)" : "0 4px 12px rgba(0,0,0,0.12)",
          },
        },
      },
      MuiSelect: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-notchedOutline": {
              borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.15)",
            },
          },
        },
      },
    },
  });
};

export default getTheme;
