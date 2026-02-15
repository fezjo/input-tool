main :: IO ()
main = do
  input <- getContents
  case words input of
    (x:_) -> putStrLn x
    [] -> return ()
